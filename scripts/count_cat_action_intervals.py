#!/usr/bin/env python3
"""Count cat action intervals per class in the source annotations.

The headline counts include every source interval, overlapping or not. The
candidate column applies the v1 filters (drop excluded labels, short
intervals and any interval that overlaps another interval in the same video);
it does not decode videos, so it can be slightly higher than the final index,
which also drops intervals past the last decodable frame.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from prepare_cat_action_v1 import (  # noqa: E402
    CLASSES, EXCLUDED_LABELS, LABEL_MAPPING, MIN_FRAMES, build_candidates,
    read_source,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(
        ROOT / "datasets/cat_raw/annotations/intervals.csv"))
    parser.add_argument("--min-frames", type=int, default=MIN_FRAMES)
    args = parser.parse_args()

    rows = read_source(Path(args.source))
    raw = Counter(row["label"] for row in rows)
    merged = Counter()
    for row in rows:
        label = row["label"]
        if label in EXCLUDED_LABELS:
            merged["（排除）" + label.split("/")[-1]] += 1
        elif label in LABEL_MAPPING:
            merged[LABEL_MAPPING[label]] += 1
        else:
            merged["（未映射）" + label] += 1

    candidates, filters, excluded, candidate_classes = build_candidates(
        rows, min_frames=args.min_frames)

    print(f"源区间总数: {len(rows)}")
    print("\n原始标签:")
    for label, count in sorted(raw.items(), key=lambda item: (-item[1], item[0])):
        target = LABEL_MAPPING.get(label, "排除" if label in EXCLUDED_LABELS else "未映射")
        print(f"  {label:34}{count:6}  -> {target}")

    print("\n七类合计（含重叠、含过短）:")
    for name in CLASSES:
        print(f"  {name:24}{merged.get(name, 0):6}")
    for name, count in sorted(merged.items()):
        if name.startswith("（排除）") or name.startswith("（未映射）"):
            print(f"  {name:24}{count:6}")

    print("\n过滤统计:")
    print(f"  排除标签: {filters['excluded_label']}")
    print(f"  时长不足 {args.min_frames} 帧: {filters['too_short']}")
    print(f"  与同视频其它区间重叠: {filters['overlapping']}")
    print(f"  保留候选: {len(candidates)}")
    print("\n去重后候选（按七类）:")
    for name in CLASSES:
        print(f"  {name:24}{candidate_classes.get(name, 0):6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
