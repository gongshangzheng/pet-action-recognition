#!/usr/bin/env python3
"""Check per-frame time mapping between source videos and the two crop arms.

Crops are written through a constant-rate pipe, so index i in a crop must be
decoded source frame i. That preserves frame order by construction, but the time
axis only matches the source when the source itself is constant frame rate. This
checker measures, per sampled video:

* whether the source is CFR or VFR, from consecutive frame PTS deltas
* whether both crops contain the same number of frames as the source
* whether crop PTS spacing is constant within a tolerance

VFR sources are reported separately instead of being silently accepted: the
experiment design forbids guessing frame numbers, so they need an explicit
decision.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import av


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-root",
        type=Path,
        required=True,
        help="full_run asset root containing metadata/, videos/gdino, videos/gdino_motion",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--sample",
        type=int,
        default=12,
        help="how many videos to check, spread evenly over the metadata list",
    )
    parser.add_argument(
        "--jitter-ms",
        type=float,
        default=1.0,
        help="largest tolerated deviation of a PTS delta from the nominal interval",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="stop reading a stream after this many frames (0 = read all)",
    )
    return parser.parse_args()


def frame_pts(path: Path, max_frames: int = 0) -> dict[str, Any]:
    """Return frame count, nominal interval and delta statistics for one stream."""
    container = av.open(str(path))
    try:
        stream = container.streams.video[0]
        rate = stream.average_rate
        nominal = 1.0 / float(rate) if rate else None
        pts: list[float] = []
        for index, frame in enumerate(container.decode(stream)):
            if frame.pts is None:
                raise RuntimeError(f"Frame without PTS in {path}")
            pts.append(float(frame.pts * frame.time_base))
            if max_frames and index + 1 >= max_frames:
                break
    finally:
        container.close()
    if len(pts) < 2:
        return {
            "frames": len(pts),
            "nominal_interval_s": nominal,
            "deltas_s": [],
        }
    deltas = [round(b - a, 6) for a, b in zip(pts, pts[1:])]
    return {
        "frames": len(pts),
        "nominal_interval_s": nominal,
        "first_pts_s": round(pts[0], 6),
        "last_pts_s": round(pts[-1], 6),
        "deltas_s": deltas,
    }


def summarize(measurement: dict[str, Any], jitter_s: float) -> dict[str, Any]:
    deltas = measurement["deltas_s"]
    nominal = measurement["nominal_interval_s"]
    if not deltas:
        return {
            "frames": measurement["frames"],
            "constant_rate": None,
            "median_interval_s": None,
            "max_deviation_s": None,
            "distinct_intervals": 0,
        }
    median = statistics.median(deltas)
    max_deviation = max(abs(value - median) for value in deltas)
    target = nominal if nominal else median
    return {
        "frames": measurement["frames"],
        "constant_rate": max(abs(value - target) for value in deltas) <= jitter_s,
        "median_interval_s": round(median, 6),
        "max_deviation_s": round(max_deviation, 6),
        "distinct_intervals": len({round(value, 4) for value in deltas}),
        "first_pts_s": measurement.get("first_pts_s"),
        "last_pts_s": measurement.get("last_pts_s"),
    }


def main() -> int:
    args = parse_args()
    asset_root = args.asset_root
    metadata_paths = sorted((asset_root / "metadata").glob("*.json"))
    if not metadata_paths:
        raise SystemExit(f"No metadata in {asset_root / 'metadata'}")
    step = max(1, len(metadata_paths) // max(1, args.sample))
    selected = metadata_paths[::step][: args.sample]
    jitter_s = args.jitter_ms / 1000.0

    results: list[dict[str, Any]] = []
    frame_count_mismatches: list[dict[str, Any]] = []
    irregular_crops: list[dict[str, Any]] = []
    vfr_sources: list[str] = []

    for metadata_path in selected:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        stem = metadata_path.stem
        source = Path(metadata["source_path"])
        crops = {
            "gdino": asset_root / "videos" / "gdino" / f"{stem}.mp4",
            "gdino_motion": asset_root
            / "videos"
            / "gdino_motion"
            / f"{stem}.mp4",
        }
        entry: dict[str, Any] = {"video": stem, "source": str(source)}
        source_summary = summarize(frame_pts(source, args.max_frames), jitter_s)
        entry["source"] = source_summary
        if source_summary["constant_rate"] is False:
            vfr_sources.append(stem)
        for arm, path in crops.items():
            summary = summarize(frame_pts(path, args.max_frames), jitter_s)
            entry[arm] = summary
            if summary["frames"] != source_summary["frames"]:
                frame_count_mismatches.append(
                    {
                        "video": stem,
                        "arm": arm,
                        "source_frames": source_summary["frames"],
                        "crop_frames": summary["frames"],
                    }
                )
            if summary["constant_rate"] is False:
                irregular_crops.append({"video": stem, "arm": arm})
        entry["index_mapping_preserved"] = (
            entry["gdino"]["frames"] == source_summary["frames"]
            and entry["gdino_motion"]["frames"] == source_summary["frames"]
        )
        results.append(entry)

    failures = {
        "frame_count_mismatch": len(frame_count_mismatches),
        "irregular_crop_spacing": len(irregular_crops),
    }
    report = {
        "schema": "cat-crop-time-mapping-v1",
        "asset_root": str(asset_root),
        "sampled": len(results),
        "available_metadata": len(metadata_paths),
        "jitter_tolerance_ms": args.jitter_ms,
        "vfr_source_count": len(vfr_sources),
        "vfr_sources": vfr_sources,
        "frame_count_mismatches": frame_count_mismatches,
        "irregular_crops": irregular_crops,
        "results": results,
        "failures": failures,
        "passed": all(count == 0 for count in failures.values()),
        "notes": [
            "crops are encoded through a constant-rate raw pipe, so frame order "
            "and index-to-index mapping are preserved by construction",
            "a VFR source cannot keep its per-frame timestamps under that pipe; "
            "the design requires an explicit decision instead of guessing frames",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "sampled": report["sampled"],
                "vfr_source_count": report["vfr_source_count"],
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
