#!/usr/bin/env python3
"""比较两套门控帧级标签（教师/同一教师的不同输入尺寸）的一致性。

用法：
  python3 scripts/checks/compare_gate_teachers.py \
      --a results/gate/labels_yolo.jsonl --b results/gate/subset_yolo1280.jsonl \
      --manifest results/gate/subset_400.csv \
      --bucket-field bucket --threshold 0.5
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path


def load(path: Path) -> dict[str, float]:
    scores: dict[str, float] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            scores[row["path"]] = float(row.get("score") or 0.0)
    return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="只比较出现在该清单里的帧")
    parser.add_argument("--bucket-field", default=None, help="按该列分组统计（如 bucket / domain）")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    scores_a, scores_b = load(args.a), load(args.b)
    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    groups = collections.defaultdict(lambda: {"n": 0, "a": 0, "b": 0, "both": 0, "flip_up": 0, "flip_down": 0})
    for row in rows:
        path = row["path"]
        if path not in scores_a or path not in scores_b:
            continue
        sa, sb = scores_a[path], scores_b[path]
        group = row.get(args.bucket_field, "all") if args.bucket_field else "all"
        cell = groups[group]
        cell["n"] += 1
        a_pos, b_pos = sa >= args.threshold, sb >= args.threshold
        cell["a"] += int(a_pos)
        cell["b"] += int(b_pos)
        cell["both"] += int(a_pos and b_pos)
        cell["flip_up"] += int(b_pos and not a_pos)
        cell["flip_down"] += int(a_pos and not b_pos)

    print(f"{'group':<14}{'n':>6}{'A+':>7}{'B+':>7}{'both':>7}{'B>A':>6}{'A>B':>6}")
    for name, cell in sorted(groups.items()):
        print(f"{name:<14}{cell['n']:>6}{cell['a']:>7}{cell['b']:>7}{cell['both']:>7}{cell['flip_up']:>6}{cell['flip_down']:>6}")
    total = sum(cell["n"] for cell in groups.values())
    both = sum(cell["both"] for cell in groups.values())
    union = sum(cell["a"] + cell["b"] - cell["both"] for cell in groups.values())
    if total:
        print(f"\n合计 {total} 帧；交集 {both}（{both / total:.1%}）；并集 {union}（{union / total:.1%}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
