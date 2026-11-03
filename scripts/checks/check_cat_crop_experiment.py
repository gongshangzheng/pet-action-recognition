#!/usr/bin/env python3
"""Audit crop videos, frame mappings and paired sample indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from petlib.datasets.cat_crop import interval_status  # noqa: E402


ARMS = ("raw", "gdino", "gdino_motion")
SPLITS = ("train", "val", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def properties(path: Path) -> dict[str, float]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cannot open {path}")
    values = {
        "frames": float(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "width": float(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    return values


def validate_metadata(video: str, asset_root: Path) -> dict[str, Any]:
    stem = Path(video).stem
    metadata_path = asset_root / "metadata" / f"{stem}.json"
    if not metadata_path.is_file():
        raise ValueError(f"missing metadata {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "complete":
        raise ValueError(f"incomplete metadata {metadata_path}")
    expected_frames = int(metadata["frames"])
    expected_size = int(metadata["size"])
    if len(metadata["track"]) != expected_frames:
        raise ValueError(f"track length mismatch for {video}")
    for arm in ("gdino", "gdino_motion"):
        path = Path(metadata[f"{arm}_video"])
        if not path.is_file():
            raise ValueError(f"missing crop {path}")
        actual = properties(path)
        if int(actual["frames"]) != expected_frames:
            raise ValueError(
                f"{arm} frame count {actual['frames']} != {expected_frames}: {path}"
            )
        if not math.isclose(actual["fps"], float(metadata["fps"]), abs_tol=0.05):
            raise ValueError(f"{arm} fps mismatch: {path}")
        if actual["width"] != expected_size or actual["height"] != expected_size:
            raise ValueError(
                f"{arm} is {actual['width']}x{actual['height']}, "
                f"expected {expected_size}x{expected_size}: {path}"
            )
        if sha256(path) != metadata[f"{arm}_video_sha256"]:
            raise ValueError(f"{arm} hash mismatch: {path}")

    source_path = Path(metadata["source_path"])
    source = properties(source_path)
    if sha256(source_path) != metadata["source_sha256"]:
        raise ValueError(f"source hash mismatch: {source_path}")
    if int(source["frames"]) != expected_frames:
        raise ValueError(
            f"source frame count {source['frames']} != {expected_frames}: {source_path}"
        )
    if not math.isclose(source["fps"], float(metadata["fps"]), abs_tol=0.05):
        raise ValueError(f"source fps mismatch: {source_path}")
    return metadata


def paired_index_audit(index_root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for split in SPLITS:
        rows = {arm: read_jsonl(index_root / f"{arm}_{split}.jsonl") for arm in ARMS}
        identity = {
            arm: [
                (
                    row["sample_id"],
                    row["label"],
                    row["start_frame"],
                    row["end_frame"],
                )
                for row in rows[arm]
            ]
            for arm in ARMS
        }
        if not (identity["raw"] == identity["gdino"] == identity["gdino_motion"]):
            raise ValueError(f"{split} arm indexes have different sample sets")
        sample_ids = [row["sample_id"] for row in rows["raw"]]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError(f"{split} contains duplicate sample_id values")
        report[split] = {
            "samples": len(sample_ids),
            "sha256": {
                arm: sha256(index_root / f"{arm}_{split}.jsonl") for arm in ARMS
            },
        }
    return report


def select_audit_videos(
    index_videos: set[str],
    requested: list[str],
    max_videos: int | None,
) -> list[str]:
    if requested and max_videos is not None:
        raise ValueError("--video cannot be combined with --max-videos")
    if max_videos is not None and max_videos < 1:
        raise ValueError("--max-videos must be positive")
    pool = requested or index_videos
    videos = sorted(set(pool))
    return videos[:max_videos] if max_videos is not None else videos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index-root",
        type=Path,
        default=ROOT / "datasets/cat_crop_classification/gdino-v1",
    )
    parser.add_argument(
        "--asset-root",
        type=Path,
        default=(
            ROOT
            / "results/cat_crop_classification/gdino-crop-20261103a/assets/gdino-v1"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=(
            ROOT
            / "results/cat_crop_classification/gdino-crop-20261103a/crop_audit.json"
        ),
    )
    parser.add_argument(
        "--video",
        action="append",
        default=[],
        help="Audit this source-relative video even when no interval is eligible",
    )
    parser.add_argument("--max-videos", type=int)
    args = parser.parse_args()

    manifest_path = args.index_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paired = paired_index_audit(args.index_root)
    index_videos = {
        row["video"]
        for split in SPLITS
        for row in read_jsonl(args.index_root / f"raw_{split}.jsonl")
    }
    videos = select_audit_videos(index_videos, args.video, args.max_videos)
    video_reports = []
    for index, video in enumerate(videos, 1):
        metadata = validate_metadata(video, args.asset_root)
        for split in SPLITS:
            for row in read_jsonl(args.index_root / f"raw_{split}.jsonl"):
                if row["video"] != video:
                    continue
                status = interval_status(
                    int(row["start_frame"]), int(row["end_frame"]), metadata["track"]
                )
                if not status["eligible"]:
                    raise ValueError(
                        f"eligible index row maps to invalid frames: {row['sample_id']}"
                    )
        video_reports.append(
            {
                "video": video,
                "frames": metadata["frames"],
                "invalid_frames": metadata["invalid_frames"],
                "corrected_frames": metadata["corrected_frames"],
                "gdino_sha256": metadata["gdino_video_sha256"],
                "gdino_motion_sha256": metadata["gdino_motion_video_sha256"],
            }
        )
        if index % 25 == 0:
            print(f"[audit] {index}/{len(videos)} videos", flush=True)
    report = {
        "schema": "cat-crop-audit-v1",
        "passed": True,
        "index_manifest": manifest,
        "paired_indexes": paired,
        "videos_checked": len(video_reports),
        "videos": video_reports,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": True,
                "videos_checked": len(video_reports),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
