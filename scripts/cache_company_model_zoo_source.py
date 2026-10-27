"""Prepare a pinned source-only RKNN Model Zoo ZIP without executing its code."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import threading
import time
from urllib.parse import quote
import zipfile

import requests

REPO = "airockchip/rknn_model_zoo"
REVISION = "bad6c7334531becaf90a561988519b7bec34d0ab"
TEXT = {".py", ".c", ".cpp", ".h", ".hpp", ".cmake", ".txt", ".md", ".json", ".yml", ".yaml", ".sh", ".in", ".mk"}


def selected(path):
    p = PurePosixPath(path)
    return not path.startswith("3rdparty/opencv/") and (
        p.suffix.lower() in TEXT or p.name in {"LICENSE", "LICENSE.txt", "CMakeLists.txt", ".gitignore"}
        or (path.startswith(("datasets/", "examples/")) and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}))


def write_json(path, data):
    temp = path.with_name(path.name + ".writing")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def verify(path, entry):
    size = path.stat().st_size
    if size != entry["size"]:
        raise ValueError("Unexpected blob size")
    git_hash = hashlib.sha1(("blob " + str(size) + "\0").encode())
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            git_hash.update(data)
            sha.update(data)
    if git_hash.hexdigest() != entry["sha"]:
        raise ValueError("Git blob hash mismatch")
    return sha.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    report = root / "results/deployment/company_assets_20260930/model_zoo_source"
    report.mkdir(parents=True, exist_ok=True)
    cache = root / ".runtime/cache/source-blobs"
    cache.mkdir(parents=True, exist_ok=True)
    tree_file = report / "tree.json"
    if tree_file.exists():
        tree = json.loads(tree_file.read_text(encoding="utf-8"))
    else:
        r = requests.get("https://api.github.com/repos/" + REPO + "/git/trees/" + REVISION + "?recursive=1", timeout=(15, 45))
        r.raise_for_status()
        tree = r.json()
        write_json(tree_file, tree)
    if tree.get("sha") != REVISION or tree.get("truncated"):
        raise ValueError("Unexpected or incomplete pinned tree")
    all_files = [x for x in tree["tree"] if x["type"] == "blob"]
    entries = [x for x in all_files if selected(x["path"])]
    for entry in entries:
        p = PurePosixPath(entry["path"])
        if p.is_absolute() or ".." in p.parts or len(entry["sha"]) != 40:
            raise ValueError("Unsafe tree entry")
    unique = {x["sha"]: x for x in entries}
    local = threading.local()
    statuses = {}

    def fetch(entry):
        path = cache / entry["sha"]
        if path.exists():
            return dict(status="verified", sha256=verify(path, entry), path=str(path.relative_to(root)))
        if not hasattr(local, "session"):
            local.session = requests.Session()
        session = local.session
        urls = ["https://raw.githubusercontent.com/" + REPO + "/" + REVISION + "/" + quote(entry["path"]), entry["url"]]
        errors = []
        part = path.with_suffix(".part")
        for url in urls:
            for attempt in range(2):
                try:
                    with session.get(url, headers={"Accept": "application/vnd.github.raw+json", "Accept-Encoding": "identity"}, stream=True, timeout=(8, 25)) as response:
                        response.raise_for_status()
                        with part.open("wb") as stream:
                            for block in response.iter_content(32768):
                                if block:
                                    stream.write(block)
                    sha = verify(part, entry)
                    os.replace(part, path)
                    return dict(status="verified", sha256=sha, path=str(path.relative_to(root)), url=url)
                except Exception as exc:
                    errors.append(str(exc))
                    if isinstance(exc, requests.HTTPError) and exc.response.status_code in (403, 404, 429):
                        break
                    time.sleep(1)
        return dict(status="failed", error="; ".join(errors[-3:]))

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch, x): x for x in unique.values()}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                statuses[entry["sha"]] = future.result()
            except Exception as exc:
                statuses[entry["sha"]] = dict(status="failed", error=str(exc))
            if len(statuses) % 20 == 0 or statuses[entry["sha"]]["status"] == "failed":
                write_json(report / "blobs_status.json", statuses)
                print("BLOBS", len(statuses), "/", len(unique), "FAILED", sum(x["status"] == "failed" for x in statuses.values()), flush=True)
    write_json(report / "blobs_status.json", statuses)
    inventory = dict(repo=REPO, revision=REVISION, included=entries,
                     excluded=[x for x in all_files if not selected(x["path"])],
                     note="Source-only snapshot: text, licenses, configs and example/calibration images; excludes bundled OpenCV SDK and binary model/runtime archives.")
    write_json(report / "snapshot_manifest.json", inventory)
    if any(x["status"] != "verified" for x in statuses.values()):
        print("SOURCE_SNAPSHOT_INCOMPLETE", flush=True)
        return 1
    target = root / "third-party/offline/sources/airockchip--rknn_model_zoo-bad6c7334531-source-only.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("Existing snapshot preserved: " + str(target))
    temp = target.with_suffix(".zip.writing")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            archive.write(cache / entry["sha"], "rknn_model_zoo-" + REVISION[:12] + "/" + entry["path"])
        archive.writestr("SOURCE_SNAPSHOT_MANIFEST.json", json.dumps(inventory, ensure_ascii=False, indent=2))
        if archive.testzip():
            raise ValueError("Snapshot ZIP CRC failed")
    os.replace(temp, target)
    write_json(report / "summary.json", dict(files=len(entries), blobs=len(unique), excluded=len(inventory["excluded"]),
               archive=str(target.relative_to(root)), size=target.stat().st_size,
               sha256=hashlib.sha256(target.read_bytes()).hexdigest(), model_executed=False))
    print("SOURCE_SNAPSHOT_VERIFIED", len(entries), target.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
