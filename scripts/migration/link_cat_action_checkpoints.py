#!/usr/bin/env python3
"""Verify existing cat-action weights and link them without copying or replacing files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_links(root: Path, source: Path, records: list[dict]) -> list[dict]:
    """Validate the whole batch before creating any directory or link."""
    root, source = root.resolve(strict=True), source.resolve(strict=True)
    planned = []
    destinations = set()
    for record in records:
        model = record["model"]
        if not model or Path(model).name != model or model in (".", ".."):
            raise ValueError(f"Unsafe model name: {model}")
        relative = Path(record["checkpoint"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe checkpoint path: {relative}")
        target = (source / relative).resolve(strict=True)
        target.relative_to(source)
        if not target.is_file() or sha256(target) != record["sha256"]:
            raise ValueError(f"Checkpoint hash mismatch: {target}")
        config = (root / record["config"]).resolve(strict=True)
        config.relative_to(root / "configs")
        if not config.is_file():
            raise ValueError(f"Missing config: {config}")
        link = root / "checkpoints" / "cat_action_v1" / model / "best.pth"
        for parent in (link.parent, *link.parent.parents):
            if parent == root:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise FileExistsError(f"Unsafe checkpoint directory: {parent}")
        if link in destinations:
            raise ValueError(f"Duplicate destination: {link}")
        destinations.add(link)
        if link.is_symlink():
            if link.resolve() != target:
                raise FileExistsError(f"Refusing to replace link: {link}")
            state = "existing"
        elif link.exists():
            raise FileExistsError(f"Refusing to replace file: {link}")
        else:
            state = "planned"
        planned.append({**record, "target": str(target), "link": str(link), "state": state})
    return planned


def apply_links(records: list[dict]) -> None:
    for record in records:
        link, target = Path(record["link"]), Path(record["target"])
        if record["state"] == "planned":
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)  # Fails if a file appeared after validation.
        if not link.is_symlink() or link.resolve(strict=True) != target:
            raise RuntimeError(f"Link verification failed: {link}")
        record["state"] = "linked"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source", type=Path,
                        default=Path("/home/wyy/pet-final/results/training/cat_action_v1"))
    parser.add_argument("--apply", action="store_true", help="Create links after checking every hash")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    manifest = json.loads((root / "configs/cat_action_v1_checkpoints.json").read_text())
    records = plan_links(root, args.source, manifest)
    if args.apply:
        apply_links(records)
        report = root / "results/migration/cat_action_v1_links.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": args.apply, "checkpoints": records}, indent=2))


if __name__ == "__main__":
    main()
