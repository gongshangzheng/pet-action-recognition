#!/usr/bin/env python3
"""Measure how stably several cats appear inside each annotated interval.

The earlier pipeline treated any sampled frame with two or more detected cats as
proof of a multi-cat interval. A single frame with two boxes is more often one
cat detected twice, so this script measures coverage (share of sampled frames
with >=2 cats) and stability (longest consecutive run of such frames) per
interval, then reports how many intervals fall above a set of thresholds.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

DROP_LABELS = {"common/multi_cat_chase", "common/multi_cat_roughplay"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--label-mapping", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping = json.loads(args.label_mapping.read_text(encoding="utf-8"))["mapping"]
    tracks: dict[str, list[dict[str, Any]]] = {}
    for path in args.metadata_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        tracks[payload["video"].split("/")[-1]] = payload["track"]

    rows = list(csv.DictReader(args.intervals.open(encoding="utf-8")))
    analysed = []
    no_detection = 0
    for row in rows:
        if row["label"] not in mapping:
            continue
        stem = row["video"].split("/")[-1]
        track = tracks.get(stem)
        if track is None:
            no_detection += 1
            continue
        start, end = int(row["start_frame"]), int(row["end_frame"])
        frames = track[max(0, start - 1) : end]
        sampled = [f for f in frames if f.get("source") in ("detected", "interpolated", "invalid")]
        if not sampled:
            continue
        flags = [(f.get("cat_count") or 0) >= 2 for f in sampled]
        coverage = sum(flags) / len(flags)
        longest = current = 0
        for flag in flags:
            current = current + 1 if flag else 0
            longest = max(longest, current)
        analysed.append(
            {
                "label": row["label"],
                "mapped": mapping[row["label"]],
                "frames": len(flags),
                "multi_frames": sum(flags),
                "coverage": coverage,
                "longest_run": longest,
            }
        )

    def count_at(min_coverage: float) -> int:
        return sum(1 for item in analysed if item["coverage"] >= min_coverage)

    def count_run(min_run: int, min_coverage: float = 0.0) -> int:
        return sum(
            1
            for item in analysed
            if item["longest_run"] >= min_run and item["coverage"] >= min_coverage
        )

    by_class = collections.defaultdict(lambda: {"intervals": 0, "stricly_multi": 0})
    for item in analysed:
        entry = by_class[item["mapped"]]
        entry["intervals"] += 1
        if item["coverage"] >= 0.5 and item["longest_run"] >= 3:
            entry["stricly_multi"] += 1

    report = {
        "schema": "multi-cat-stability-v1",
        "intervals_total": len(rows),
        "intervals_with_detection": len(analysed),
        "intervals_without_detection": no_detection,
        "coverage_thresholds": {
            f">={value:.1f}": count_at(value) for value in (0.1, 0.3, 0.5, 0.8, 1.0)
        },
        "stable_run_thresholds": {
            f"run>={run}": count_run(run) for run in (2, 3, 5, 10)
        },
        "combined_rules": {
            "coverage>=0.5 and run>=3": count_run(3, 0.5),
            "coverage>=0.8 and run>=3": count_run(3, 0.8),
            "coverage>=0.5 and run>=2": count_run(2, 0.5),
        },
        "coverage_median": round(
            statistics.median([item["coverage"] for item in analysed]), 4
        )
        if analysed
        else None,
        "per_class": {
            key: dict(value) for key, value in sorted(by_class.items())
        },
        "notes": [
            "coverage is the share of decoded frames in the interval whose cat_count is >= 2",
            "longest_run counts consecutive such frames in decode order",
            "a high threshold on both coverage and run length rejects single-frame duplicate detections",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("intervals_with_detection", "intervals_without_detection", "coverage_thresholds", "combined_rules")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
