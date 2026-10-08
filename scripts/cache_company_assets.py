"""Cache public model assets without importing models or executing downloaded code."""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import time
from urllib.parse import quote, urlparse
import zipfile

import requests
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--report-dir", default="results/deployment/company_assets_20260930",
                    help="Project-relative report directory; separate only for disjoint asset sets")
    ap.add_argument("--only", help="Comma-separated asset id prefixes")
    ap.add_argument("--discover-only", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--refresh-manifest", action="store_true", help="Repeat discovery using cached upstream metadata")
    ap.add_argument("--verify-only", action="store_true", help="Verify files without network downloads")
    args = ap.parse_args()
    root = args.root.resolve()
    out = (root / args.report_dir).resolve()
    out.relative_to(root)
    out.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((root / "configs/company_offline_assets.json").read_text(encoding="utf-8"))
    manifest_path = out / "manifest.json"
    manifest = {"assets": [], "discovery_errors": [], "notes": catalog["notes"]}
    headers = {"User-Agent": "pet-project-offline-cache/1.0", "Accept-Encoding": "identity"}

    def safe(relative):
        path = (root / relative).resolve()
        path.relative_to(root)
        return path

    def metadata(url):
        cached = out / "upstream" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))["response"]
        error = None
        candidates = [url]
        if url.startswith("https://huggingface.co/"):
            candidates = [url.replace("https://huggingface.co/", "https://hf-mirror.com/"), url]
        for attempt in range(max(3, len(candidates))):
            try:
                selected_url = candidates[min(attempt, len(candidates) - 1)]
                response = requests.get(selected_url, headers=headers, timeout=(15, 45))
                response.raise_for_status()
                data = response.json()
                dump(cached, {"url": url, "retrieved_from": selected_url, "retrieved_at": time.time(), "response": data})
                return data
            except Exception as exc:
                error = exc
                if isinstance(exc, requests.HTTPError) and response.status_code in (403, 404):
                    break
                time.sleep(attempt + 1)
        raise RuntimeError(str(error))

    def add(identifier, url, path, purpose, **extra):
        safe(path)
        manifest["assets"].append(dict(id=identifier, urls=[url] if isinstance(url, str) else url,
                                       path=path, purpose=purpose, **extra))

    def discover():
        tree = ast.parse((root / "server/routers/training.py").read_text(encoding="utf-8"))
        registry = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "_MMACTION2_REGISTRY" for t in n.targets))
        by_url = {}
        for model in registry:
            url = model.get("pretrained_url")
            if not url:
                continue
            path = "checkpoints/{0}/{0}_pretrained.pth".format(model["id"])
            if url in by_url:
                by_url[url]["aliases"].append(path)
                by_url[url]["models"].append(model)
                continue
            add("mmaction:" + model["id"], url, path, "registered action model pretrained checkpoint",
                aliases=[".runtime/cache/torch/hub/checkpoints/" + urlparse(url).path.rsplit("/", 1)[-1]],
                models=[model])
            by_url[url] = manifest["assets"][-1]
        for filename in catalog["torchvision"]:
            add("torchvision:" + filename, "https://download.pytorch.org/models/" + filename,
                "checkpoints/torchvision/" + filename, "classification / segmentation / initialization backbone",
                aliases=[".runtime/cache/torch/hub/checkpoints/" + filename],
                sha256_prefix=filename.rsplit("-", 1)[-1].split(".")[0])
        for release in catalog["github_releases"]:
            repo, tag = release["repo"], release["tag"]
            print("DISCOVER release " + repo + " " + tag, flush=True)
            try:
                data = metadata("https://api.github.com/repos/" + repo + "/releases/tags/" + tag)
                names = {a["name"]: a for a in data["assets"]}
            except Exception as exc:
                names = {}
                manifest.setdefault("warnings", []).append("release metadata " + repo + ": " + str(exc))
            selected = set(release.get("files", []))
            selected.update(n for n in names if any(fnmatch.fnmatch(n, p) for p in release.get("patterns", [])))
            if not selected:
                manifest["discovery_errors"].append("No release assets matched " + repo)
            for name in sorted(selected):
                detail = names.get(name, {})
                sha = detail.get("digest") or ""
                browser_url = detail.get("browser_download_url") or "https://github.com/" + repo + "/releases/download/" + tag + "/" + quote(name)
                urls = ([detail["url"] + "?download=1", browser_url] if detail.get("url") else [browser_url])
                urls = release.get("alternate_urls", {}).get(name, []) + urls
                add("release:" + repo + ":" + name,
                    urls,
                    release["directory"] + "/" + name, release["purpose"],
                    request_headers={"Accept": "application/octet-stream"},
                    aliases=["weights/" + name] if repo == "ultralytics/assets" and name.endswith(".pt") else [],
                    md5=release.get("md5", {}).get(name),
                    size=detail.get("size"), sha256=release.get("sha256", {}).get(name) or
                    (sha.removeprefix("sha256:") if sha.startswith("sha256:") else None))
        for source in catalog["github_sources"]:
            repo, ref = source["repo"], source.get("ref", "HEAD")
            print("DISCOVER source " + repo + " " + ref, flush=True)
            try:
                try:
                    data = metadata("https://api.github.com/repos/" + repo + "/commits/" + ref)
                except Exception:
                    if ref == "HEAD":
                        raise
                    data = metadata("https://api.github.com/repos/" + repo + "/commits/HEAD")
                    manifest.setdefault("warnings", []).append(repo + " ref " + ref + " unavailable; snapshot HEAD " + data["sha"])
                sha = data["sha"]
                add("source:" + repo, ["https://codeload.github.com/" + repo + "/zip/" + sha,
                                      "https://api.github.com/repos/" + repo + "/zipball/" + sha,
                                      "https://codeload.github.com/" + repo + "/legacy.zip/" + sha],
                    "third-party/offline/sources/" + repo.replace("/", "--") + "-" + sha[:12] + ".zip",
                    "upstream source, configurations, license and examples", revision=sha, requested_ref=ref)
            except Exception as exc:
                manifest["discovery_errors"].append("source " + repo + ": " + str(exc))
        for hf in catalog["huggingface"]:
            repo = hf["repo"]
            print("DISCOVER HF " + repo, flush=True)
            try:
                if hf.get("snapshot_file"):
                    data = json.loads(safe(hf["snapshot_file"]).read_text(encoding="utf-8"))
                    if data["repo"] != repo:
                        raise ValueError("Snapshot repository mismatch")
                else:
                    data = metadata("https://huggingface.co/api/models/" + repo + "/revision/main?blobs=true")
                sha = data["sha"]
                for item in data["siblings"]:
                    name = item["rfilename"]
                    if not any(fnmatch.fnmatch(name, p) for p in hf["patterns"]):
                        continue
                    lfs = item.get("lfs") or {}
                    urls = ["https://hf-mirror.com/" + repo + "/resolve/" + sha + "/" + name,
                            "https://huggingface.co/" + repo + "/resolve/" + sha + "/" + name]
                    if hf.get("modelscope_mirror") and item.get("modelscope_revision"):
                        urls.insert(0, "https://www.modelscope.cn/models/" + hf["modelscope_mirror"] +
                                    "/resolve/" + item["modelscope_revision"] + "/" + quote(name))
                    add("hf:" + repo + ":" + name, urls,
                        hf["directory"] + "/" + name, "complete local model / tokenizer / processor files",
                        aliases=[".runtime/cache/huggingface/hub/models--" + repo.replace("/", "--") + "/snapshots/" + sha + "/" + name],
                        size=item.get("size"), sha256=item.get("sha256") or lfs.get("sha256") or lfs.get("oid"), revision=sha)
            except Exception as exc:
                manifest["discovery_errors"].append("HF " + repo + ": " + str(exc))
        for mirror in catalog.get("modelscope", []):
            repo = mirror["repo"]
            print("DISCOVER ModelScope " + repo, flush=True)
            try:
                data = metadata("https://www.modelscope.cn/api/v1/models/" + repo + "/repo/files?Revision=master&Recursive=true")
                items = {entry["Path"]: entry for entry in data["Data"]["Files"] if entry["Type"] == "blob"}
                for name in mirror["files"]:
                    entry = items[name]
                    revision = entry["Revision"]
                    add("modelscope:" + repo + ":" + name,
                        "https://www.modelscope.cn/models/" + repo + "/resolve/" + revision + "/" + quote(name),
                        mirror["directory"] + "/" + name, mirror["purpose"],
                        size=entry["Size"], sha256=entry["Sha256"], revision=revision)
            except Exception as exc:
                manifest["discovery_errors"].append("ModelScope " + repo + ": " + str(exc))
        rk = catalog["rknn_repository"]
        print("DISCOVER RKNN platform files", flush=True)
        try:
            commit = metadata("https://api.github.com/repos/" + rk["repo"] + "/commits/" + rk["ref"])["sha"]
            tree = metadata("https://api.github.com/repos/" + rk["repo"] + "/git/trees/" + commit + "?recursive=1")
            if tree.get("truncated"):
                raise RuntimeError("Git tree response truncated")
            selected = []
            for item in tree["tree"]:
                name = item["path"]
                if item["type"] != "blob":
                    continue
                doc = name.startswith("doc/") and name.lower().endswith((".pdf", ".md", ".txt"))
                runtime = name.startswith("rknpu2/") and name.endswith(("librknnrt.so", "rknn_api.h", "rknn_server"))
                lite = "lite" in name and name.endswith(".whl") and "cp310" in name and "linux" in name
                root_note = "/" not in name and name.lower().startswith(("readme", "license", "changelog"))
                if doc or runtime or lite or root_note:
                    selected.append(name)
                    suffix = rk["repo"] + "/" + commit + "/" + quote(name)
                    add("rknn-file:" + name,
                        [item["url"], "https://raw.githubusercontent.com/" + suffix,
                         "https://media.githubusercontent.com/media/" + suffix],
                        "third-party/offline/rknn-toolkit2-2.3.2/" + name,
                        "RKNN docs and board-side materials; archive only, not installed", revision=commit,
                        request_headers={"Accept": "application/vnd.github.raw+json"},
                        size=item["size"], git_blob_sha1=item["sha"])
            if not selected:
                raise RuntimeError("No matching RKNN files")
        except Exception as exc:
            manifest["discovery_errors"].append("RKNN files: " + str(exc))
        for item in catalog.get("extra_assets", []):
            add(**item)
        tag_rank = {tag: rank for rank, tag in enumerate(sys_tags())}
        for requirement in catalog.get("optional_packages", []):
            name, version = requirement.split("==", 1)
            print("DISCOVER optional package " + requirement, flush=True)
            try:
                data = metadata("https://pypi.org/pypi/" + name + "/" + version + "/json")
                choices = []
                for entry in data["urls"]:
                    if entry["packagetype"] == "bdist_wheel":
                        wheel_tags = parse_wheel_filename(entry["filename"])[3]
                        ranks = [tag_rank[tag] for tag in wheel_tags if tag in tag_rank]
                        if ranks:
                            choices.append((min(ranks), entry))
                    elif entry["packagetype"] == "sdist":
                        choices.append((1000000, entry))
                if not choices:
                    raise RuntimeError("No matching wheel or source distribution")
                entry = min(choices, key=lambda pair: pair[0])[1]
                add("optional-package:" + requirement, entry["url"],
                    ".runtime/cache/optional-wheels/" + entry["filename"],
                    "optional candidate dependency, cache only; not installed",
                    size=entry["size"], sha256=entry["digests"]["sha256"],
                    distribution_type=entry["packagetype"],
                    requires_dist=data["info"].get("requires_dist"),
                    requires_python=data["info"].get("requires_python"))
            except Exception as exc:
                manifest["discovery_errors"].append("optional package " + requirement + ": " + str(exc))
        manifest["created_at"] = time.time()
        dump(manifest_path, manifest)

    if manifest_path.exists() and not args.refresh_manifest:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        discover()
    if args.discover_only:
        print("DISCOVERY_DONE " + str(len(manifest["assets"])), flush=True)
        return 0
    result_path = out / "assets_status.json"
    previous = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {"assets": {}}
    results = previous["assets"]
    for item in manifest["assets"]:
        old = results.get(item["id"], {})
        if old.get("status") == "verified" and old.get("path") == item["path"]:
            if not item.get("sha256"):
                item["sha256"] = old["sha256"]

    def validate(path, item):
        length = path.stat().st_size
        if not length or (item.get("size") and length != item["size"]):
            raise ValueError("Empty or unexpected byte count: " + str(length))
        with path.open("rb") as stream:
            head = stream.read(300)
        if head.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<?xml")):
            raise ValueError("Downloaded an error page, not an asset")
        if head.startswith(b"version https://git-lfs.github.com/spec/"):
            raise ValueError("Downloaded Git LFS pointer, not asset content")
        if item["path"].endswith(".pdf") and not head.startswith(b"%PDF-"):
            raise ValueError("Downloaded content is not a PDF")
        sha = digest(path)
        if item.get("sha256") and sha != item["sha256"]:
            raise ValueError("Upstream SHA256 mismatch")
        if item.get("sha256_prefix") and not sha.startswith(item["sha256_prefix"]):
            raise ValueError("Upstream SHA256 prefix mismatch")
        if item.get("md5") and digest(path, "md5") != item["md5"]:
            raise ValueError("Upstream MD5 mismatch")
        if item.get("git_blob_sha1"):
            git_hash = hashlib.sha1(("blob " + str(length) + "\0").encode())
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    git_hash.update(block)
            if git_hash.hexdigest() != item["git_blob_sha1"]:
                raise ValueError("Upstream Git blob SHA1 mismatch")
        if item["path"].endswith((".zip", ".whl")):
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError("ZIP CRC failure: " + bad)
        if item["path"].endswith((".pt", ".pth", ".ckpt")) and not (head.startswith(b"PK") or head.startswith(b"\x80") or tarfile.is_tarfile(path)):
            raise ValueError("Unrecognized PyTorch checkpoint envelope")
        return dict(size=length, sha256=sha)

    def download(item):
        started = time.time()
        target = safe(item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        errors = []
        final_url = None
        try:
            if target.exists():
                detail = validate(target, item)
            else:
                if args.verify_only:
                    raise FileNotFoundError("Asset is not cached")
                # Older versions rejected valid legacy tar-format PyTorch checkpoints.
                for rejected in sorted(target.parent.glob(target.name + ".part.rejected.*")):
                    try:
                        detail = validate(rejected, item)
                        os.link(rejected, target)
                        break
                    except (ValueError, OSError):
                        continue
                success = False
                if target.exists():
                    success = True
                for url in ([] if success else item["urls"]):
                    for attempt in range(3):
                        try:
                            offset = part.stat().st_size if part.exists() else 0
                            request_headers = dict(headers)
                            request_headers.update(item.get("request_headers", {}))
                            if offset:
                                request_headers["Range"] = "bytes=" + str(offset) + "-"
                            with requests.get(url, headers=request_headers, timeout=(20, 75), stream=True) as response:
                                if response.status_code == 416 and offset:
                                    if response.headers.get("Content-Range") != "bytes */" + str(offset):
                                        raise ValueError("Cannot validate completed range length")
                                    detail = validate(part, item)
                                else:
                                    response.raise_for_status()
                                    resume = offset and response.status_code == 206
                                    if resume and not response.headers.get("Content-Range", "").startswith("bytes " + str(offset) + "-"):
                                        raise ValueError("Unexpected range response")
                                    if not resume:
                                        offset = 0
                                    expected = response.headers.get("Content-Length")
                                    read = 0
                                    with part.open("ab" if resume else "wb") as stream:
                                        for block in response.iter_content(chunk_size=1024 * 1024):
                                            if block:
                                                stream.write(block)
                                                read += len(block)
                                            if time.time() - started > 2400:
                                                raise TimeoutError("Per-asset time budget exceeded; partial file kept")
                                    if expected is not None and read != int(expected):
                                        raise ValueError("Incomplete HTTP payload")
                                    detail = validate(part, item)
                                final_url = response.url.split("?", 1)[0]
                            os.replace(part, target)
                            success = True
                            break
                        except Exception as exc:
                            errors.append(str(exc))
                            if isinstance(exc, ValueError) and part.exists():
                                # Retain rejected bytes for inspection without resuming them as valid content.
                                rejected = part.with_name(part.name + ".rejected." + str(time.time_ns()))
                                part.rename(rejected)
                            if isinstance(exc, requests.HTTPError) and response.status_code in (403, 404):
                                break
                            time.sleep(1 + attempt)
                    if success:
                        break
                if not success:
                    raise RuntimeError("; ".join(errors[-4:]))
            for relative in item.get("aliases", []):
                alias = safe(relative)
                alias.parent.mkdir(parents=True, exist_ok=True)
                if alias.exists():
                    if digest(alias) != detail["sha256"]:
                        raise ValueError("Existing alias differs; not overwritten: " + relative)
                else:
                    try:
                        os.link(target, alias)
                    except OSError:
                        shutil.copyfile(target, alias)
            for model in item.get("models", []):
                model_id = model["id"]
                meta_path = root / ("checkpoints/{0}/{0}_pretrained.json".format(model_id))
                dump(meta_path, dict(type="pretrained", model_id=model_id,
                                     checkpoint_path="checkpoints/{0}/{0}_pretrained.pth".format(model_id),
                                     url=item["urls"][0], pretrained_source=model.get("pretrained_source"), **detail))
            return dict(status="verified", path=item["path"], urls=item["urls"], final_url=final_url,
                        elapsed_s=round(time.time() - started, 2), **detail)
        except Exception as exc:
            return dict(status="failed", path=item["path"], urls=item["urls"], error=str(exc),
                        elapsed_s=round(time.time() - started, 2))

    selected = [a for a in manifest["assets"] if not args.only or
                any(a["id"].startswith(prefix) for prefix in args.only.split(","))]
    if args.retry_failed:
        selected = [a for a in selected if results.get(a["id"], {}).get("status") != "verified"]
    selected.sort(key=lambda a: (0 if a["id"].startswith("optional-package:") else 1,
                                 a.get("size") or 32 * 1024 * 1024))

    def save():
        for hf in catalog["huggingface"]:
            prefix = "hf:" + hf["repo"] + ":"
            group = [a for a in manifest["assets"] if a["id"].startswith(prefix)]
            if group and all(results.get(a["id"], {}).get("status") == "verified" for a in group):
                revision = group[0]["revision"]
                ref = safe(".runtime/cache/huggingface/hub/models--" + hf["repo"].replace("/", "--") + "/refs/main")
                if not ref.exists():
                    ref.parent.mkdir(parents=True, exist_ok=True)
                    ref.write_text(revision, encoding="utf-8")
                elif ref.read_text(encoding="utf-8").strip() != revision:
                    print("WARNING existing HF main ref differs; use explicit local model directory", flush=True)
        verified = [r for r in results.values() if r["status"] == "verified"]
        failed = [r for r in results.values() if r["status"] == "failed"]
        dump(result_path, dict(assets=results, verified=len(verified), failed=len(failed),
                              total=len(manifest["assets"]), bytes=sum(r["size"] for r in verified),
                              discovery_errors=manifest["discovery_errors"], model_executed=False,
                              weights_deserialized=False, environment_changed=False, updated_at=time.time()))

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as pool:
        futures = {pool.submit(download, a): a for a in selected}
        for future in as_completed(futures):
            item = futures[future]
            result = future.result()
            results[item["id"]] = result
            save()
            print(result["status"].upper() + " " + item["id"] + " " +
                  (str(result.get("size", "")) if result["status"] == "verified" else result["error"]), flush=True)
    save()
    print("ASSET_CACHE_PASS_FINISHED", flush=True)
    return int(any(r["status"] == "failed" for r in results.values()) or bool(manifest["discovery_errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
