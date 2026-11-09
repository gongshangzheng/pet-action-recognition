#!/usr/bin/env python3
"""Compare follow-camera metadata without decoding source or rendered video."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.datasets.cat_crop import interval_status  # noqa: E402

SCHEMA = "cat-crop-camera-summary-v2"
ELIGIBILITY_FIELDS = ("valid", "reason", "target_class", "camera_box")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def required_int(data: dict[str, Any], name: str, path: Path) -> int:
    value = data.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{path}: {name} must be an integer")
    return value


def box_for_motion(
    record: dict[str, Any], *, fallback_camera: bool
) -> list[float] | None:
    value = record.get("display_box")
    if value is None and fallback_camera:
        value = record.get("camera_box")
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"invalid display/camera box: {value!r}")
    box = [float(item) for item in value]
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"box has no positive area: {value!r}")
    return box


def distribution(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "p95": None, "max": None}
    ordered = sorted(values)
    rank = (len(ordered) - 1) * 0.95
    lower = math.floor(rank)
    upper = math.ceil(rank)
    p95 = (
        ordered[lower]
        if lower == upper
        else ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower])
    )
    return {
        "mean": round(math.fsum(values) / len(values), 12),
        "p95": round(p95, 12),
        "max": round(max(values), 12),
    }


def motion_diagnostics(
    track: list[dict[str, Any]], *, fallback_camera: bool
) -> dict[str, Any]:
    """Measure consecutive display-box center and side changes."""
    centers: list[float] = []
    sides: list[float] = []
    boxes = [
        box_for_motion(record, fallback_camera=fallback_camera)
        for record in track
    ]
    for previous, current in zip(boxes, boxes[1:]):
        if previous is None or current is None:
            continue
        previous_side = max(previous[2] - previous[0], previous[3] - previous[1])
        current_side = max(current[2] - current[0], current[3] - current[1])
        previous_center = (
            (previous[0] + previous[2]) / 2,
            (previous[1] + previous[3]) / 2,
        )
        current_center = (
            (current[0] + current[2]) / 2,
            (current[1] + current[3]) / 2,
        )
        centers.append(
            math.hypot(
                current_center[0] - previous_center[0],
                current_center[1] - previous_center[1],
            )
            / ((previous_side + current_side) / 2)
        )
        sides.append(abs(math.log(current_side / previous_side)))
    return {
        "basis": (
            "display_box_with_camera_box_fallback"
            if fallback_camera
            else "display_box_only"
        ),
        "camera_box_fallback": fallback_camera,
        "consecutive_box_pairs": len(centers),
        "normalized_center_step": distribution(centers),
        "abs_log_side_step": distribution(sides),
    }


def summarize_metadata(
    path: Path, *, fallback_camera: bool
) -> dict[str, Any]:
    data = read_json(path)
    track = data.get("track") if isinstance(data, dict) else None
    if not isinstance(track, list) or not all(
        isinstance(record, dict) for record in track
    ):
        raise ValueError(f"{path}: track must be an array of objects")
    valid_values = [record.get("valid") for record in track]
    if any(not isinstance(value, bool) for value in valid_values):
        raise ValueError(f"{path}: every track record needs boolean valid")
    source_hash = data.get("source_sha256")
    fingerprint = data.get("detection_fingerprint")
    if not isinstance(source_hash, str) or not source_hash:
        raise ValueError(f"{path}: source_sha256 must be non-empty")
    if not isinstance(fingerprint, dict):
        raise ValueError(f"{path}: detection_fingerprint must be an object")
    return {
        "total_frames": len(track),
        "valid_frames": sum(valid_values),
        "display_missing_letterbox_frames": sum(
            box_for_motion(record, fallback_camera=fallback_camera) is None
            for record in track
        ),
        "pixel_motion_frames_from_metadata": required_int(
            data, "corrected_frames", path
        ),
        "base_trajectory_motion": motion_diagnostics(
            track, fallback_camera=fallback_camera
        ),
        "_track": track,
        "_source_sha256": source_hash,
        "_detection_fingerprint": fingerprint,
    }


def counted(
    states: Sequence[dict[str, Any]],
    key: str,
    normalize: Callable[[Any], str] = str,
) -> dict[str, int]:
    return dict(sorted(Counter(normalize(state.get(key)) for state in states).items()))


def summarize_detection(path: Path) -> dict[str, Any]:
    data = read_json(path)
    anchors = data.get("anchors") if isinstance(data, dict) else None
    if not isinstance(anchors, dict):
        raise ValueError(f"{path}: anchors must be an object")
    states = list(anchors.values())
    if not all(isinstance(state, dict) for state in states):
        raise ValueError(f"{path}: every anchor must be an object")
    state_counts = {
        "anchor_count": len(states),
        "target_valid": counted(
            states, "target_valid", lambda value: str(bool(value)).lower()
        ),
        "target_class": counted(
            states, "target_class", lambda value: "none" if value is None else str(value)
        ),
        "cat_count": counted(states, "cat_count"),
        "dog_count": counted(states, "dog_count"),
        "pet_count": counted(states, "pet_count"),
        "reasons": dict(
            sorted(
                Counter(
                    reason
                    for state in states
                    for reason in state.get("reasons", [])
                ).items()
            )
        ),
    }
    return {
        "state_counts": state_counts,
        "_source_sha256": data.get("source_sha256"),
        "_fingerprint": data.get("fingerprint"),
    }


def changed_count(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    fields: Sequence[str],
) -> int | None:
    if len(left) != len(right):
        return None
    return sum(
        any(a.get(field) != b.get(field) for field in fields)
        for a, b in zip(left, right)
    )


def compare_tracks(
    left: list[dict[str, Any]], right: list[dict[str, Any]]
) -> dict[str, Any]:
    length_equal = len(left) == len(right)
    changed = changed_count(left, right, ELIGIBILITY_FIELDS)
    return {
        "lengths_equal": length_equal,
        "valid_flags_changed_frames": changed_count(left, right, ("valid",)),
        "camera_boxes_changed_frames": changed_count(left, right, ("camera_box",)),
        "eligibility_fields_changed_frames": changed,
        "eligibility_track_unchanged": length_equal and changed == 0,
    }


def public(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if not key.startswith("_")}


def build_report(
    asset_root: Path, baseline_root: Path, selection_path: Path
) -> dict[str, Any]:
    selection = read_json(selection_path)
    rows = selection.get("rows") if isinstance(selection, dict) else None
    if not isinstance(rows, list):
        raise ValueError("selection must contain a rows array")
    videos: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        video = row.get("video") if isinstance(row, dict) else None
        if not isinstance(video, str) or not video:
            raise ValueError(f"selection row {index}: video must be non-empty")
        stem = Path(video).stem
        asset = summarize_metadata(
            asset_root / "metadata" / f"{stem}.json", fallback_camera=False
        )
        baseline = summarize_metadata(
            baseline_root / "metadata" / f"{stem}.json", fallback_camera=True
        )
        asset_detection = summarize_detection(
            asset_root / "detections" / f"{stem}.json"
        )
        baseline_detection = summarize_detection(
            baseline_root / "detections" / f"{stem}.json"
        )
        start_frame = row.get("start_frame")
        end_frame = row.get("end_frame")
        if not isinstance(start_frame, int) or not isinstance(end_frame, int):
            raise ValueError(f"{video}: start_frame/end_frame must be integers")
        asset_status = interval_status(start_frame, end_frame, asset["_track"])
        baseline_status = interval_status(
            start_frame, end_frame, baseline["_track"]
        )
        asset_source = asset["_source_sha256"]
        baseline_source = baseline["_source_sha256"]
        asset_fingerprint = asset["_detection_fingerprint"]
        baseline_fingerprint = baseline["_detection_fingerprint"]
        state_asset = public(asset_detection)
        state_baseline = public(baseline_detection)
        videos.append(
            {
                "q_id": row.get("q_id", f"Q{index:03d}"),
                "sample_id": row.get("sample_id"),
                "video": video,
                "selected_frames_1based": [start_frame, end_frame],
                "asset": public(asset),
                "baseline": public(baseline),
                "comparison": {
                    "source_sha256": {
                        "asset": asset_source,
                        "baseline": baseline_source,
                        "identical": asset_source == baseline_source,
                        "asset_metadata_matches_detection": (
                            asset_source == asset_detection["_source_sha256"]
                        ),
                        "baseline_metadata_matches_detection": (
                            baseline_source == baseline_detection["_source_sha256"]
                        ),
                    },
                    "detection_fingerprint": {
                        "asset": asset_fingerprint,
                        "baseline": baseline_fingerprint,
                        "identical": asset_fingerprint == baseline_fingerprint,
                        "asset_metadata_matches_detection": (
                            asset_fingerprint == asset_detection["_fingerprint"]
                        ),
                        "baseline_metadata_matches_detection": (
                            baseline_fingerprint == baseline_detection["_fingerprint"]
                        ),
                    },
                    "selected_eligibility": {
                        "asset": asset_status,
                        "baseline": baseline_status,
                        "unchanged": asset_status == baseline_status,
                    },
                    "track_eligibility": compare_tracks(
                        asset["_track"], baseline["_track"]
                    ),
                    "detection_state_counts": {
                        "asset": state_asset,
                        "baseline": state_baseline,
                        "identical": state_asset == state_baseline,
                    },
                },
            }
        )
    comparisons = [video["comparison"] for video in videos]
    return {
        "schema": SCHEMA,
        "basis_notice": (
            "Base trajectory diagnostics use metadata boxes. They are not the "
            "actual C-arm rendered path and do not measure crop quality."
        ),
        "acceptance_thresholds_applied": False,
        "metric_definitions": {
            "display_missing_letterbox_frames": (
                "Frames whose selected base camera box is null: display_box for "
                "the asset, and display_box with camera_box fallback for the "
                "baseline. This is a metadata base-track diagnostic, not the "
                "actual rendered-path letterbox count."
            ),
            "pixel_motion_frames_from_metadata": "metadata.corrected_frames.",
            "box_side": "max(box_width, box_height).",
            "normalized_center_step": (
                "Euclidean center distance divided by mean current/previous side."
            ),
            "abs_log_side_step": (
                "absolute natural log of current side divided by previous side."
            ),
            "distribution": (
                "Arithmetic mean, linearly interpolated p95, and maximum."
            ),
            "track_eligibility_unchanged": (
                "Equal length and unchanged valid/reason/target_class/camera_box."
            ),
        },
        "selection": {"path": str(selection_path), "count": len(videos)},
        "videos": videos,
        "totals": {
            "count": len(videos),
            "asset_frames": sum(video["asset"]["total_frames"] for video in videos),
            "baseline_frames": sum(
                video["baseline"]["total_frames"] for video in videos
            ),
            "asset_valid_frames": sum(
                video["asset"]["valid_frames"] for video in videos
            ),
            "baseline_valid_frames": sum(
                video["baseline"]["valid_frames"] for video in videos
            ),
            "asset_motion_frames": sum(
                video["asset"]["pixel_motion_frames_from_metadata"]
                for video in videos
            ),
            "baseline_motion_frames": sum(
                video["baseline"]["pixel_motion_frames_from_metadata"]
                for video in videos
            ),
            "all_source_hashes_identical": all(
                item["source_sha256"]["identical"] for item in comparisons
            ),
            "all_fingerprints_identical": all(
                item["detection_fingerprint"]["identical"]
                for item in comparisons
            ),
            "all_selected_eligibility_unchanged": all(
                item["selected_eligibility"]["unchanged"] for item in comparisons
            ),
            "all_track_eligibility_unchanged": all(
                item["track_eligibility"]["eligibility_track_unchanged"]
                for item in comparisons
            ),
            "all_state_counts_identical": all(
                item["detection_state_counts"]["identical"]
                for item in comparisons
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build_report(
        args.asset_root.expanduser(),
        args.baseline_root.expanduser(),
        args.selection.expanduser(),
    )
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    output = args.out.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".writing")
    temporary.write_text(encoded + "\n", encoding="utf-8")
    os.replace(temporary, output)
    print(encoded, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
