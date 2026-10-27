#!/usr/bin/env python3
"""Copy this project's useful local state to the lab 4090 with SHA-256 verification."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import time

import paramiko

ROOT = Path(__file__).resolve().parents[1]
LOCAL_REPORT = ROOT / "results" / "migration_lab"
SOURCE_CONNECTION = ROOT / "自作自偷" / "4090.txt"
HOST_KEYS = ROOT / "results" / "lab_known_hosts"
HOST = "115.154.235.243"
PORT = 22108
USER = "wyy"
TARGET = "/home/wyy/pet-final"
STAGING = "/home/wyy/.pet-final-transfer"
TOP_DIRS = (
    ".claude", ".github", "configs", "data", "docs", "evaluation", "management",
    "models", "openspec", "papers", "petlib", "scripts", "server", "templates", "web",
)
RESULT_SUBDIRS = ("deployment", "model_comparison", "research", "datasets", "local-service", "live")
ROOT_FILES = (".gitattributes", ".gitignore", "AGENTS.md", "README.md", "start_services.sh",
              "最终方案图.jpg", "项目要求.txt")
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".tmp", ".part"}
READ_SIZE = 1024 * 1024


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(READ_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if not relative or "\n" in relative or "\r" in relative or "\\" in relative:
        fail(f"Unsupported source filename: {relative!r}")
    return relative


def iter_tree(path: Path):
    if not path.exists():
        return
    for base, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(base) / d).is_symlink())
        for filename in sorted(files):
            candidate = Path(base) / filename
            if candidate.is_symlink() or filename.endswith(tuple(SKIP_SUFFIXES)):
                continue
            if candidate.is_file():
                yield candidate


def collect_paths() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name in ROOT_FILES:
        path = ROOT / name
        if path.is_file() and not path.is_symlink():
            result[safe_relative(path)] = path
    for directory in TOP_DIRS:
        for path in iter_tree(ROOT / directory):
            result[safe_relative(path)] = path
    for path in iter_tree(ROOT / "datasets" / "cat_raw"):
        result[safe_relative(path)] = path
    for directory in RESULT_SUBDIRS:
        for path in iter_tree(ROOT / "results" / directory):
            result[safe_relative(path)] = path
    return result


def lab_annotations() -> dict[str, Path]:
    """Make Linux address copies; original and portable annotations stay unchanged."""
    source = ROOT / "datasets" / "cat_raw" / "annotations"
    output = LOCAL_REPORT / "generated"
    output.mkdir(parents=True, exist_ok=True)
    with (source / "merged_annotations.relative.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or "video" not in fields:
            fail("Invalid portable CSV annotations")
        rows = list(reader)
    tasks = json.loads((source / "merged_annotations.relative.json").read_text(encoding="utf-8"))

    def remote_video(relative: str) -> str:
        if not relative.startswith("videos/") or ".." in Path(relative).parts or "\\" in relative:
            fail(f"Unsafe portable video path: {relative!r}")
        if not (ROOT / "datasets" / "cat_raw" / relative).is_file():
            fail(f"Missing portable video: {relative}")
        return TARGET + "/datasets/cat_raw/" + relative

    for row in rows:
        row["video"] = remote_video(row["video"])
    csv_path = output / "merged_annotations.lab.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for task in tasks:
        task["data"]["video"] = remote_video(task["data"]["video"])
    json_path = output / "merged_annotations.lab.json"
    json_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note = output / "LAB_SERVER_README.md"
    note.write_text(
        "# 课题组服务器迁移说明\n\n"
        "项目目录：`/home/wyy/pet-final`。猫视频：`datasets/cat_raw/videos/`。\n"
        "原始标注：`datasets/cat_raw/annotations/original/`。\n"
        "Linux 绝对路径副本：`datasets/cat_raw/annotations/merged_annotations.lab.csv` "
        "和 `.lab.json`。相对路径版 `.relative.*` 也可用。\n"
        "从 Windows 同步的 `.local.*` 仅用于来源记录，服务器训练应选 `.lab.*` 或 "
        "`.relative.*`。`intervals.csv` 保留动作的帧起止、重叠和原任务 ID；\n"
        "默认 MMAction2 整视频单标签 VideoDataset 仍需片段/区间适配。\n"
        "原有课题组项目 `/home/wyy/pet-action-recognition`、已有 checkpoint 和 "
        "`/home/wyy/miniconda3/envs/pet` 保留在原位置。\n",
        encoding="utf-8",
    )
    return {
        "datasets/cat_raw/annotations/merged_annotations.lab.csv": csv_path,
        "datasets/cat_raw/annotations/merged_annotations.lab.json": json_path,
        "LAB_SERVER_README.md": note,
    }


def prepare() -> dict:
    LOCAL_REPORT.mkdir(parents=True, exist_ok=True)
    bundle = LOCAL_REPORT / "git_history.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=ROOT, check=True)
    files = collect_paths()
    files.update(lab_annotations())
    seen = set()
    entries = []
    for relative, path in sorted(files.items()):
        folded = relative.casefold()
        if folded in seen:
            fail(f"Case-insensitive filename collision: {relative}")
        seen.add(folded)
        info = path.stat()
        entries.append(dict(path=relative, source=str(path), bytes=info.st_size,
                            mtime_ns=info.st_mtime_ns, sha256=sha256_file(path)))
    manifest = dict(schema="pet-final-lab-migration-v1", git_head=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        target=TARGET, files=entries, total_bytes=sum(e["bytes"] for e in entries),
        git_bundle=dict(path=str(bundle), bytes=bundle.stat().st_size, sha256=sha256_file(bundle)),
        excluded=["自作自偷/4090.txt", "自作自偷/cat_raw.tar.part-*", ".venv/",
                  "web/node_modules/", "results/npm-cache/", "results/migration_lab/", ".pi/"],
        absent_from_local=["company server checkpoints (~7.96 GiB); only historical manifest is local"])
    (LOCAL_REPORT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (LOCAL_REPORT / "manifest.sha256").open("w", encoding="utf-8", newline="") as handle:
        for entry in entries:
            handle.write(f"{entry['sha256']}  {entry['path']}\n")
    print(f"MIGRATION_PREPARED files={len(entries)} bytes={manifest['total_bytes']} bundle={bundle.stat().st_size}",
          flush=True)
    return manifest


def read_password() -> str:
    text = SOURCE_CONNECTION.read_text(encoding="utf-8")
    match = re.search(r"(?im)^\s*pwd\s*:\s*([^\r\n]+)", text)
    if match is None:
        fail("Connection file has no pwd field")
    return match.group(1).strip()


def connect() -> paramiko.SSHClient:
    if not HOST_KEYS.is_file():
        fail("Pinned SSH host key is missing")
    client = paramiko.SSHClient()
    client.load_host_keys(str(HOST_KEYS))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(HOST, port=PORT, username=USER, password=read_password(),
                   allow_agent=False, look_for_keys=False, timeout=20, auth_timeout=20)
    return client


def remote_run(client: paramiko.SSHClient, command: str, *, checked: bool = True) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(command, timeout=120)
    status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if checked and status:
        fail(f"Remote command failed ({status}): {command}\n{err[:1500]}{out[:1500]}")
    return status, out, err


def remote_exists(sftp: paramiko.SFTPClient, path: str):
    try:
        return sftp.stat(path)
    except FileNotFoundError:
        return None


def mkdir_p(sftp: paramiko.SFTPClient, path: str) -> None:
    current = ""
    for component in path.strip("/").split("/"):
        current += "/" + component
        info = remote_exists(sftp, current)
        if info is None:
            sftp.mkdir(current)
        elif not stat.S_ISDIR(info.st_mode):
            fail(f"Remote path is not a directory: {current}")


def upload(sftp: paramiko.SFTPClient, source: Path, destination: str, expected_size: int,
           *, replace_pristine_clone_file: bool = False) -> str:
    if source.stat().st_size != expected_size:
        fail(f"Local source changed size: {source}")
    mkdir_p(sftp, destination.rsplit("/", 1)[0])
    done = remote_exists(sftp, destination)
    if done is not None:
        if not stat.S_ISREG(done.st_mode):
            fail(f"Remote destination is not a regular file: {destination}")
        if replace_pristine_clone_file:
            # Only a Git-tracked file whose clone checkout is still pristine may be replaced.
            pass
        elif done.st_size == expected_size:
            return "already_present_pending_final_hash"
        else:
            fail(f"Remote destination conflicts: {destination}")
    temporary = destination + ".codex-upload"
    pending = remote_exists(sftp, temporary)
    offset = pending.st_size if pending is not None else 0
    if offset > expected_size:
        fail(f"Oversized remote partial file: {temporary}")
    with source.open("rb") as local:
        local.seek(offset)
        with sftp.open(temporary, "ab") as remote:
            remote.set_pipelined(True)
            for block in iter(lambda: local.read(READ_SIZE), b""):
                remote.write(block)
    actual = sftp.stat(temporary).st_size
    if actual != expected_size:
        fail(f"Incomplete upload: {destination}: {actual}/{expected_size}")
    if not replace_pristine_clone_file and remote_exists(sftp, destination) is not None:
        fail(f"Remote destination appeared during upload: {destination}")
    if replace_pristine_clone_file:
        sftp.posix_rename(temporary, destination)
    else:
        sftp.rename(temporary, destination)
    return "uploaded"


def transfer() -> dict:
    manifest = json.loads((LOCAL_REPORT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "pet-final-lab-migration-v1" or manifest.get("target") != TARGET:
        fail("Invalid local migration manifest")
    bundle = Path(manifest["git_bundle"]["path"])
    if sha256_file(bundle) != manifest["git_bundle"]["sha256"]:
        fail("Git bundle changed since manifest preparation")
    client = connect()
    try:
        sftp = client.open_sftp()
        try:
            remote_run(client, "test -d /home/wyy && test -w /home/wyy")
            mkdir_p(sftp, STAGING)
            bundle_remote = STAGING + "/git_history_" + manifest["git_bundle"]["sha256"][:16] + ".bundle"
            upload(sftp, bundle, bundle_remote, bundle.stat().st_size)
            current = remote_exists(sftp, TARGET)
            if current is None:
                remote_run(client, "git clone -q -- " + shlex.quote(bundle_remote) + " " + shlex.quote(TARGET))
            elif not stat.S_ISDIR(current.st_mode):
                fail("Target project path exists but is not a directory")
            _, head, _ = remote_run(client, "git -C " + shlex.quote(TARGET) + " rev-parse HEAD")
            if head.strip() != manifest["git_head"]:
                _, dirty, _ = remote_run(client, "git -C " + shlex.quote(TARGET)
                                         + " status --porcelain --untracked-files=no")
                if dirty.strip():
                    fail("Remote worktree changed; refusing to update Git history")
                remote_run(client, "git -C " + shlex.quote(TARGET) + " fetch -q "
                           + shlex.quote(bundle_remote) + " main")
                remote_run(client, "git -C " + shlex.quote(TARGET) + " merge --ff-only -q FETCH_HEAD")
                _, head, _ = remote_run(client, "git -C " + shlex.quote(TARGET) + " rev-parse HEAD")
                if head.strip() != manifest["git_head"]:
                    fail("Remote Git head does not match local bundle")
            _, tracked_output, _ = remote_run(client, "git -C " + shlex.quote(TARGET) + " ls-files -z")
            _, modified_output, _ = remote_run(client, "git -C " + shlex.quote(TARGET)
                                               + " diff --name-only -z")
            tracked = set(filter(None, tracked_output.split("\0")))
            modified = set(filter(None, modified_output.split("\0")))
            pristine_tracked = tracked - modified
            mkdir_p(sftp, TARGET + "/.migration")
            transferred = skipped = transferred_bytes = 0
            started = time.monotonic()
            for index, entry in enumerate(manifest["files"], 1):
                source = Path(entry["source"])
                info = source.stat()
                if (info.st_size, info.st_mtime_ns) != (entry["bytes"], entry["mtime_ns"]):
                    fail(f"Local source changed after manifest creation: {source}")
                dest = TARGET + "/" + entry["path"]
                state = upload(sftp, source, dest, entry["bytes"],
                               replace_pristine_clone_file=entry["path"] in pristine_tracked)
                transferred += state == "uploaded"
                skipped += state != "uploaded"
                transferred_bytes += entry["bytes"] if state == "uploaded" else 0
                if index % 100 == 0 or index == len(manifest["files"]):
                    print(f"UPLOAD {index}/{len(manifest['files'])} new={transferred} "
                          f"sent_GiB={transferred_bytes/2**30:.2f} elapsed_s={time.monotonic()-started:.0f}",
                          flush=True)
            upload(sftp, LOCAL_REPORT / "manifest.sha256", TARGET + "/.migration/manifest.sha256",
                   (LOCAL_REPORT / "manifest.sha256").stat().st_size)
            upload(sftp, LOCAL_REPORT / "manifest.json", TARGET + "/.migration/manifest.json",
                   (LOCAL_REPORT / "manifest.json").stat().st_size)
            print("REMOTE_HASH_CHECK_START", flush=True)
            remote_run(client, "cd " + shlex.quote(TARGET) + " && sha256sum --quiet -c .migration/manifest.sha256")
            report = dict(target=TARGET, files=len(manifest["files"]),
                          bytes=manifest["total_bytes"], newly_uploaded=transferred,
                          skipped_after_size_check=skipped, remote_sha256_verified=True,
                          completed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          git_head=manifest["git_head"], public_assets_missing_from_local=True)
            report_path = LOCAL_REPORT / "transfer_report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            upload(sftp, report_path, TARGET + "/.migration/transfer_report.json", report_path.stat().st_size)
            print("LAB_TRANSFER_DONE " + json.dumps(report, ensure_ascii=False), flush=True)
            return report
        finally:
            sftp.close()
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true", help="Create Git bundle and SHA-256 manifest locally")
    group.add_argument("--transfer", action="store_true", help="Upload and verify prepared manifest")
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare()
        else:
            transfer()
        return 0
    except (OSError, ValueError, RuntimeError, paramiko.SSHException, subprocess.CalledProcessError) as exc:
        print(f"LAB_MIGRATION_FAILED {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
