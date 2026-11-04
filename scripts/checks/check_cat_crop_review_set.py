#!/usr/bin/env python3
"""Audit a raw/GroundingDINO/motion browser review set."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


ARMS = ("raw", "gdino", "gdino_motion")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,nb_frames,duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(result.stdout).get("streams") or []
    if len(streams) != 1:
        raise ValueError(f"Expected one video stream in {path}")
    stream = streams[0]
    frames = stream.get("nb_frames")
    duration = stream.get("duration")
    rate = stream.get("avg_frame_rate")
    if frames in (None, "N/A") or duration in (None, "N/A") or not rate:
        raise ValueError(f"Missing frame/duration/FPS metadata in {path}")
    return {
        "frames": int(frames),
        "fps": float(Fraction(rate)),
        "duration": float(duration),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
    }


def audit_set(set_root: Path) -> dict[str, Any]:
    manifest_path = set_root / "items.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("mode") != "crop_comparison":
        raise ValueError(f"Expected crop_comparison mode: {manifest_path}")

    declared_paths: set[str] = set()
    items: list[dict[str, Any]] = []
    for item in manifest.get("items") or []:
        review_id = item["review_id"]
        expected_frames = int(item["frame_count"])
        properties: dict[str, dict[str, Any]] = {}
        hashes: dict[str, str] = {}
        for arm in ARMS:
            relative = (item.get("files") or {}).get(arm)
            if not relative:
                raise ValueError(f"{review_id} has no {arm} file")
            if relative in declared_paths:
                raise ValueError(f"Duplicate review media path: {relative}")
            declared_paths.add(relative)
            media_path = set_root / relative
            if not media_path.is_file():
                raise ValueError(f"Missing review media: {media_path}")
            properties[arm] = probe_video(media_path)
            hashes[arm] = sha256(media_path)

        raw = properties["raw"]
        for arm in ARMS:
            actual = properties[arm]
            if actual["frames"] != expected_frames:
                raise ValueError(
                    f"{review_id}/{arm} has {actual['frames']} frames, "
                    f"expected {expected_frames}"
                )
            if actual["width"] != 512 or actual["height"] != 512:
                raise ValueError(
                    f"{review_id}/{arm} is "
                    f"{actual['width']}x{actual['height']}, expected 512x512"
                )
            if not math.isclose(actual["fps"], raw["fps"], abs_tol=0.01):
                raise ValueError(f"{review_id}/{arm} FPS differs from raw")
            if not math.isclose(
                actual["duration"], raw["duration"], abs_tol=0.05
            ):
                raise ValueError(f"{review_id}/{arm} duration differs from raw")

        items.append(
            {
                "review_id": review_id,
                "sample_id": item["sample_id"],
                "class_name": item["class_name"],
                "frame_count": expected_frames,
                "strict_available": bool(item.get("strict_available")),
                "properties": properties,
                "sha256": hashes,
            }
        )
        print(
            f"[audit] {review_id}: {item['class_name']} frames={expected_frames}",
            flush=True,
        )

    actual_paths: set[str] = set()
    for path in (set_root / "media").glob("*/*.mp4"):
        actual_paths.add(path.relative_to(set_root).as_posix())
    if actual_paths != declared_paths:
        missing = sorted(declared_paths - actual_paths)
        extra = sorted(actual_paths - declared_paths)
        raise ValueError(f"Declared media mismatch: missing={missing}, extra={extra}")

    selection_hash = None
    selection = manifest.get("selection")
    if selection:
        selection_path = Path(selection)
        if selection_path.is_file():
            selection_hash = sha256(selection_path)
            expected_hash = manifest.get("selection_sha256")
            if expected_hash and selection_hash != expected_hash:
                raise ValueError("Selection SHA-256 does not match manifest")

    report = {
        "schema": "cat-crop-review-audit-v1",
        "passed": True,
        "set": set_root.name,
        "count": len(items),
        "selection_sha256": selection_hash,
        "items": items,
    }
    output = set_root / "audit.json"
    temporary = output.with_suffix(".json.writing")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-root", type=Path, required=True)
    args = parser.parse_args()
    report = audit_set(args.set_root)
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "count": report["count"],
                "audit": str(args.set_root / "audit.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
