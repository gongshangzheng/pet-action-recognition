#!/usr/bin/env python3
"""Verify that the two crop arms share one detection cache and the same anchors.

The experiment compares arm B (GroundingDINO crop) with arm C (the same crop
plus pixel-motion assistance). For that comparison to attribute a difference to
motion assistance alone, both arms must come from one detection cache, and every
frame that carries a detection (``source == "detected"``) must be cropped by the
same box in both arms. Frames outside the anchor set, the warmup prefix and
invalid frames must not receive motion assistance either.

The check reads the render metadata written by
``scripts/prepare_cat_crop_experiment.py`` and, for a small deterministic
sample, compares decoded frames of the two encoded videos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-root",
        type=Path,
        required=True,
        help="full_run asset root containing metadata/, videos/gdino, videos/gdino_motion",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="where to write the JSON report",
    )
    parser.add_argument(
        "--pixel-videos",
        type=int,
        default=3,
        help="how many videos to compare by decoding frames",
    )
    parser.add_argument(
        "--pixel-anchors",
        type=int,
        default=3,
        help="how many detected frames to compare per sampled video",
    )
    parser.add_argument(
        "--max-mean-pixel-diff",
        type=float,
        default=3.0,
        help="largest tolerated mean absolute difference on anchor frames",
    )
    parser.add_argument(
        "--max-frame-pixel-diff",
        type=int,
        default=24,
        help="largest tolerated per-pixel difference on anchor frames",
    )
    return parser.parse_args()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compare_video(
    stem: str, asset_root: Path, anchor_limit: int
) -> dict[str, Any]:
    """Compare every frame of the two encoded crops and group by detection state."""
    left = asset_root / "videos" / "gdino" / f"{stem}.mp4"
    right = asset_root / "videos" / "gdino_motion" / f"{stem}.mp4"
    metadata = json.loads(
        (asset_root / "metadata" / f"{stem}.json").read_text(encoding="utf-8")
    )
    track = metadata["track"]
    warmup = int(metadata.get("render_fingerprint", {}).get("bg_warmup_frames", 0))

    capture_left = cv2.VideoCapture(str(left))
    capture_right = cv2.VideoCapture(str(right))
    if not capture_left.isOpened() or not capture_right.isOpened():
        capture_left.release()
        capture_right.release()
        raise RuntimeError(f"Cannot open one of the two crops for {stem}")

    groups: dict[str, list[float]] = {
        "anchor": [],
        "interpolated_after_warmup": [],
        "interpolated_in_warmup": [],
        "invalid": [],
    }
    frame_rows: list[dict[str, Any]] = []
    index = 0
    try:
        while True:
            ok_left, frame_left = capture_left.read()
            ok_right, frame_right = capture_right.read()
            if not ok_left or not ok_right:
                break
            if index >= len(track):
                raise RuntimeError(f"Decoded more frames than metadata for {stem}")
            record = track[index]
            source = record.get("source")
            if source == "detected":
                group = "anchor"
            elif source == "invalid":
                group = "invalid"
            elif index < warmup:
                group = "interpolated_in_warmup"
            else:
                group = "interpolated_after_warmup"
            delta = np.abs(
                frame_left.astype(np.int16) - frame_right.astype(np.int16)
            )
            mean_diff = float(delta.mean())
            groups[group].append(mean_diff)
            frame_rows.append(
                {
                    "frame": index,
                    "group": group,
                    "mean_abs_diff": round(mean_diff, 4),
                    "max_abs_diff": int(delta.max()),
                }
            )
            index += 1
    finally:
        capture_left.release()
        capture_right.release()

    summary = {}
    for name, values in groups.items():
        if not values:
            summary[name] = {"frames": 0}
            continue
        summary[name] = {
            "frames": len(values),
            "median_mean_abs_diff": round(float(np.median(values)), 4),
            "p90_mean_abs_diff": round(float(np.percentile(values, 90)), 4),
            "max_mean_abs_diff": round(max(values), 4),
        }

    anchor_rows = [row for row in frame_rows if row["group"] == "anchor"]
    return {
        "video": stem,
        "frames": index,
        "corrected_frames": metadata.get("corrected_frames"),
        "warmup_frames": warmup,
        "group_summary": summary,
        "anchor_samples": anchor_rows[:anchor_limit],
        "anchor_max_abs_diff": max(
            (row["max_abs_diff"] for row in anchor_rows), default=0
        ),
        "largest_anchor_means": sorted(
            anchor_rows, key=lambda row: row["mean_abs_diff"], reverse=True
        )[:5],
    }


def main() -> int:
    args = parse_args()
    asset_root = args.asset_root
    metadata_dir = asset_root / "metadata"
    if not metadata_dir.is_dir():
        raise SystemExit(f"Missing metadata directory: {metadata_dir}")

    paths = sorted(metadata_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"No render metadata in {metadata_dir}")

    detection_fingerprints: dict[str, int] = {}
    render_fingerprints: dict[str, int] = {}
    incomplete: list[str] = []
    missing_videos: list[str] = []
    corrected: list[tuple[str, int]] = []

    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        stem = path.stem
        if metadata.get("status") != "complete":
            incomplete.append(stem)
        for key in ("gdino_video", "gdino_motion_video"):
            reference = metadata.get(key)
            if not reference or not Path(reference).is_file():
                missing_videos.append(f"{stem}:{key}")
        detection_key = json.dumps(
            metadata.get("detection_fingerprint"), sort_keys=True
        )
        render_key = json.dumps(metadata.get("render_fingerprint"), sort_keys=True)
        detection_fingerprints[detection_key] = (
            detection_fingerprints.get(detection_key, 0) + 1
        )
        render_fingerprints[render_key] = render_fingerprints.get(render_key, 0) + 1
        corrected_frames = int(metadata.get("corrected_frames") or 0)
        if corrected_frames > 0:
            corrected.append((stem, corrected_frames))

    sample: list[str] = []
    corrected_sorted = sorted(corrected, key=lambda item: item[1], reverse=True)
    for stem, _ in corrected_sorted[: args.pixel_videos]:
        sample.append(stem)
    if len(sample) < args.pixel_videos:
        step = max(1, len(paths) // max(1, args.pixel_videos))
        for path in paths[::step]:
            if path.stem in sample:
                continue
            sample.append(path.stem)
            if len(sample) >= args.pixel_videos:
                break

    pixel_checks = [
        compare_video(stem, asset_root, args.pixel_anchors) for stem in sample
    ]

    anchor_median_failures = [
        {
            "video": item["video"],
            "anchor_median_mean_abs_diff": item["group_summary"]["anchor"][
                "median_mean_abs_diff"
            ],
        }
        for item in pixel_checks
        if item["group_summary"]["anchor"].get("frames", 0) > 0
        and item["group_summary"]["anchor"]["median_mean_abs_diff"]
        > args.max_mean_pixel_diff
    ]

    discrimination = []
    for item in pixel_checks:
        summary = item["group_summary"]
        anchor_median = summary["anchor"].get("median_mean_abs_diff")
        assisted = summary["interpolated_after_warmup"].get("median_mean_abs_diff")
        discrimination.append(
            {
                "video": item["video"],
                "corrected_frames": item["corrected_frames"],
                "anchor_median": anchor_median,
                "interpolated_after_warmup_median": assisted,
                "assisted_exceeds_anchor": (
                    anchor_median is not None
                    and assisted is not None
                    and assisted > anchor_median
                ),
            }
        )

    failures = {
        "fingerprint_variants": max(
            0, len(detection_fingerprints) - 1
        ),
        "render_fingerprint_variants": max(0, len(render_fingerprints) - 1),
        "incomplete_metadata": len(incomplete),
        "missing_videos": len(missing_videos),
        "anchor_median_above_threshold": len(anchor_median_failures),
    }
    report = {
        "schema": "cat-crop-arm-consistency-v2",
        "asset_root": str(asset_root),
        "metadata_files": len(paths),
        "videos_with_motion_correction": len(corrected),
        "detection_fingerprint_variants": len(detection_fingerprints),
        "render_fingerprint_variants": len(render_fingerprints),
        "detection_fingerprint_sha256": sorted(
            sha256_text(key) for key in detection_fingerprints
        ),
        "incomplete_count": len(incomplete),
        "incomplete_samples": incomplete[:20],
        "missing_video_count": len(missing_videos),
        "missing_video_samples": missing_videos[:20],
        "pixel_thresholds": {"max_anchor_median_mean_abs_diff": args.max_mean_pixel_diff},
        "pixel_checks": pixel_checks,
        "anchor_median_failures": anchor_median_failures,
        "discrimination": discrimination,
        "failures": failures,
        "passed": all(count == 0 for count in failures.values()),
        "notes": [
            "camera_box in metadata records the strict eligibility box, not the "
            "rendered arm C camera path; anchor equality is therefore measured on "
            "decoded frames of the two videos, not on metadata boxes",
            "mean_abs_diff includes H.264 quantization noise between two separate "
            "encodes of the same crop",
        ],
    }
    report["script_sha256"] = sha256(Path(__file__).resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": report["passed"], "failures": failures}, ensure_ascii=False))
    print(json.dumps(discrimination, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
