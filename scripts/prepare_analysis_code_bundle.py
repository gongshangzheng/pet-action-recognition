"""Build a scoped, checksummed source archive without importing project models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile


ROOT_FILES = ("AGENTS.md", "README.md", ".gitignore")
SOURCE_DIRS = (
    "scripts", "configs", "server", "petlib", "evaluation", "models",
    "openspec", "docs", "templates",
)
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist",
    ".pytest_cache", ".mypy_cache", "outputs", "work_dirs",
}
SKIP_SUFFIXES = {".html", ".htm", ".pyc", ".pyo", ".db", ".pth", ".pt", ".ckpt"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    out.relative_to(repo / "results")
    out.mkdir(parents=True, exist_ok=True)
    archive_path = out / "analysis_code_source.tar.gz"
    if archive_path.exists():
        raise SystemExit("Use a new output directory; source archive already exists")

    paths = [repo / name for name in ROOT_FILES if (repo / name).is_file()]
    excluded = []
    for directory in SOURCE_DIRS:
        start = repo / directory
        if not start.is_dir():
            continue
        for current, dirs, files in os.walk(str(start), followlinks=False):
            base = Path(current)
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS
                             and not d.endswith(".egg-info")
                             and not (base / d).is_symlink())
            for name in sorted(files):
                path = base / name
                if (path.is_symlink() or path.suffix.lower() in SKIP_SUFFIXES
                        or name.startswith(".env")):
                    excluded.append(path.relative_to(repo).as_posix())
                    continue
                paths.append(path)
    paths.sort(key=lambda p: p.relative_to(repo).as_posix())
    records = [{"path": p.relative_to(repo).as_posix(), "bytes": p.stat().st_size,
                "sha256": sha256(p)} for p in paths]
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), text=True).strip()
    manifest = {
        "schema": 1, "source_revision": revision,
        "destination": "/home/work/analysis_code",
        "scope": "Source transfer only; no dependency installation or model execution",
        "included_roots": list(ROOT_FILES + SOURCE_DIRS),
        "excluded_roots": [".git", ".claude", ".pi", ".venv", "web", "data",
                           "results", "checkpoints", "datasets", "management", "papers"],
        "root_user_documents_included": False, "reading_html_included": False,
        "local_checkpoint_directory_exists": (repo / "checkpoints").exists(),
        "local_dataset_directory_exists": (repo / "datasets").exists(),
        "excluded_files_in_selected_roots": excluded,
        "file_count": len(records), "total_bytes": sum(x["bytes"] for x in records),
        "files": records,
    }
    manifest_path = out / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    with tarfile.open(str(archive_path), "w:gz", compresslevel=6) as archive:
        for path in paths:
            info = archive.gettarinfo(str(path), arcname=path.relative_to(repo).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if path.suffix == ".sh" else 0o644
            with path.open("rb") as stream:
                archive.addfile(info, stream)
        archive.add(str(manifest_path), arcname=".deployment/source_manifest.json")
    receipt = {"archive": str(archive_path), "archive_bytes": archive_path.stat().st_size,
               "archive_sha256": sha256(archive_path), "source_revision": revision,
               "file_count": len(records), "source_bytes": manifest["total_bytes"]}
    (out / "bundle_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
