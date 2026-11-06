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


BOX_TOLERANCE = 1e-6


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def box_equal(left: list[float] | None, right: list[float] | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if len(left) != len(right):
        return False
    return all(abs(a - b) <= BOX_TOLERANCE for a, b in zip(left, right))


def read_frame(capture: cv2.VideoCapture, index: int) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    if not ok or frame is None:
        raise RuntimeError(f"Cannot decode frame {index}")
    return frame


def compare_video(
    stem: str, asset_root: Path, max_anchors: int
) -> dict[str, Any]:
    left = asset_root / "videos" / "gdino" / f"{stem}.mp4"
    right = asset_root / "videos" / "gdino_motion" / f"{stem}.mp4"
    metadata = json.loads(
        (asset_root / "metadata" / f"{stem}.json").read_text(encoding="utf-8")
    )
    anchors = [
        record["frame"]
        for record in metadata["track"]
        if record.get("source") == "detected"
    ][:max_anchors]
    if not anchors:
        return {"video": stem, "anchors": [], "skipped": "no detected frame"}

    capture_left = cv2.VideoCapture(str(left))
    capture_right = cv2.VideoCapture(str(right))
    if not capture_left.isOpened() or not capture_right.isOpened():
        capture_left.release()
        capture_right.release()
        raise RuntimeError(f"Cannot open one of the two crops for {stem}")

    results = []
    try:
        for anchor in anchors:
            frame_left = read_frame(capture_left, anchor).astype(np.int16)
            frame_right = read_frame(capture_right, anchor).astype(np.int16)
            if frame_left.shape != frame_right.shape:
                raise RuntimeError(f"Frame shape mismatch at {stem}:{anchor}")
            delta = np.abs(frame_left - frame_right)
            results.append(
                {
                    "frame": anchor,
                    "mean_abs_diff": round(float(delta.mean()), 4),
                    "max_abs_diff": int(delta.max()),
                }
            )
    finally:
        capture_left.release()
        capture_right.release()
    return {"video": stem, "anchors": results}


def main() -> int:
    args = parse_args()
    asset_root = args.asset_root
    metadata_dir = asset_root / "metadata"
    if not metadata_dir.is_dir():
        raise SystemExit(f"Missing metadata directory: {metadata_dir}")

    paths = sorted(metadata_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"No render metadata in {metadata_dir}")

    detection_fingerprints: dict[str, list[str]] = {}
    render_fingerprints: dict[str, list[str]] = {}
    anchor_frames = 0
    anchor_mismatches: list[dict[str, Any]] = []
    anchor_missing_camera: list[dict[str, Any]] = []
    assisted_invalid: list[dict[str, Any]] = []
    assisted_during_warmup: list[dict[str, Any]] = []
    missing_videos: list[str] = []
    incomplete: list[str] = []

    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        stem = path.stem
        if metadata.get("status") != "complete":
            incomplete.append(stem)
        for key in ("gdino_video", "gdino_motion_video"):
            reference = metadata.get(key)
            if not reference:
                missing_videos.append(f"{stem}:{key}=null")
                continue
            if not Path(reference).is_file():
                missing_videos.append(f"{stem}:{key}")

        detection_fingerprint = json.dumps(
            metadata.get("detection_fingerprint"), sort_keys=True
        )
        render_fingerprint = json.dumps(
            metadata.get("render_fingerprint"), sort_keys=True
        )
        detection_fingerprints.setdefault(detection_fingerprint, []).append(stem)
        render_fingerprints.setdefault(render_fingerprint, []).append(stem)

        warmup = int(metadata.get("render_fingerprint", {}).get("bg_warmup_frames", 0))
        for record in metadata["track"]:
            frame = record.get("frame")
            source = record.get("source")
            camera_box = record.get("camera_box")
            display_box = record.get("display_box")
            if source == "detected":
                anchor_frames += 1
                if display_box is None:
                    continue
                if camera_box is None:
                    anchor_missing_camera.append({"video": stem, "frame": frame})
                elif not box_equal(camera_box, display_box):
                    anchor_mismatches.append(
                        {
                            "video": stem,
                            "frame": frame,
                            "camera_box": camera_box,
                            "display_box": display_box,
                        }
                    )
            elif source == "invalid" and camera_box is not None:
                assisted_invalid.append({"video": stem, "frame": frame})
            if (
                source == "interpolated"
                and frame is not None
                and frame < warmup
                and not box_equal(camera_box, display_box)
            ):
                assisted_during_warmup.append(
                    {
                        "video": stem,
                        "frame": frame,
                        "camera_box": camera_box,
                        "display_box": display_box,
                    }
                )

    pixel_checks = []
    if args.pixel_videos > 0:
        step = max(1, len(paths) // args.pixel_videos)
        for path in paths[::step][: args.pixel_videos]:
            pixel_checks.append(
                compare_video(path.stem, asset_root, args.pixel_anchors)
            )

    pixel_failures = [
        {"video": item["video"], **anchor}
        for item in pixel_checks
        for anchor in item["anchors"]
        if anchor["mean_abs_diff"] > args.max_mean_pixel_diff
        or anchor["max_abs_diff"] > args.max_frame_pixel_diff
    ]

    report = {
        "schema": "cat-crop-arm-consistency-v1",
        "asset_root": str(asset_root),
        "metadata_files": len(paths),
        "detection_fingerprint_variants": len(detection_fingerprints),
        "detection_fingerprint_samples": {
            key: len(value) for key, value in detection_fingerprints.items()
        },
        "render_fingerprint_variants": len(render_fingerprints),
        "render_fingerprint_samples": {
            key: len(value) for key, value in render_fingerprints.items()
        },
        "anchor_frames": anchor_frames,
        "anchor_mismatches": anchor_mismatches[:20],
        "anchor_mismatch_count": len(anchor_mismatches),
        "anchor_missing_camera_count": len(anchor_missing_camera),
        "assisted_invalid_count": len(assisted_invalid),
        "assisted_invalid_samples": assisted_invalid[:20],
        "assisted_during_warmup_count": len(assisted_during_warmup),
        "assisted_during_warmup_samples": assisted_during_warmup[:20],
        "incomplete_count": len(incomplete),
        "incomplete_samples": incomplete[:20],
        "missing_video_count": len(missing_videos),
        "missing_video_samples": missing_videos[:20],
        "pixel_checks": pixel_checks,
        "pixel_failures": pixel_failures,
        "pixel_thresholds": {
            "max_mean_abs_diff": args.max_mean_pixel_diff,
            "max_abs_diff": args.max_frame_pixel_diff,
        },
        "detected_frame_source_values": {
            "anchor": "detected",
            "interpolated": "interpolated",
            "invalid": "invalid",
        },
    }

    failures = {
        "anchor_mismatch": len(anchor_mismatches),
        "anchor_missing_camera": len(anchor_missing_camera),
        "assisted_invalid": len(assisted_invalid),
        "assisted_during_warmup": len(assisted_during_warmup),
        "detection_cache_variants": max(0, len(detection_fingerprints) - 1),
        "render_fingerprint_variants": max(0, len(render_fingerprints) - 1),
        "incomplete_metadata": len(incomplete),
        "missing_videos": len(missing_videos),
        "pixel_anchor_mismatch": len(pixel_failures),
    }
    report["failures"] = failures
    report["passed"] = all(count == 0 for count in failures.values())
    report["script_sha256"] = sha256(Path(__file__).resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": report["passed"], "failures": failures}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
