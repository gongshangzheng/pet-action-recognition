#!/usr/bin/env python3
"""选样脚本：从稳定多宠物区间（覆盖 ≥0.5 且连续 ≥3 锚点）按视频随机取 N 段。

口径与 cat-data-preprocessing evidence 2026-11-07 统计一致：
- 区间来自 intervals.csv（9 类闭集标签，丢弃 multi_cat_chase/roughplay）
- 锚点 = 检测缓存中 frame % sample_stride == 0 的帧
- 多宠物 = 锚点上 cat_count + dog_count >= 2
- 覆盖率 = 区间内多宠物锚点占比；连续 = 最长连续多宠物锚点数

先全量统计命中区间数（对照 565），再按视频去重后随机抽 N 段，种子写死可复现。

用法（本地，零 GPU）：
    python3 scripts/select_multi_pet_eval.py \
        --intervals /path/to/intervals.csv \
        --detections-dir /path/to/detections \
        --out results/tracking_eval_20261107/eval_set_v1.json
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from build_cat_dataset_slices import (  # noqa: E402  复用既有口径实现
    DROPPED_LABELS,
    LABEL_MAP,
    anchors_in,
    longest_run,
    pet_flags,
)


def load_detections(detection_dir: Path) -> dict[str, dict]:
    caches = {}
    for path in detection_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        caches[payload["video"].split("/")[-1].rsplit(".", 1)[0]] = payload
    return caches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--detections-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-videos", type=int, default=10)
    parser.add_argument("--pet-coverage", type=float, default=0.5)
    parser.add_argument("--pet-run", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261107)
    args = parser.parse_args()

    caches = load_detections(args.detections_dir)
    rows = list(csv.DictReader(args.intervals.open(encoding="utf-8")))

    hits = []
    stats = {"intervals_total": len(rows), "with_detection": 0, "stable_multi": 0}
    for row in rows:
        label = row["label"]
        if label in DROPPED_LABELS or label not in LABEL_MAP:
            continue
        stem = row["video"].split("/")[-1].rsplit(".", 1)[0]
        cache = caches.get(stem)
        if cache is None:
            continue
        stats["with_detection"] += 1
        start, end = int(row["start_frame"]), int(row["end_frame"])
        states = anchors_in(cache, start, end)
        flags = pet_flags(states)
        if not flags:
            continue
        coverage = sum(flags) / len(flags)
        run = longest_run(flags)
        if coverage >= args.pet_coverage and run >= args.pet_run:
            stats["stable_multi"] += 1
            hits.append(
                {
                    "video": row["video"],
                    "stem": stem,
                    "label": LABEL_MAP[label],
                    "start_frame": start,
                    "end_frame": end,
                    "anchors": len(flags),
                    "multi_anchors": sum(flags),
                    "coverage": round(coverage, 4),
                    "longest_run": run,
                }
            )

    # 按视频去重后随机抽 N 段视频，每视频取其首个稳定区间
    videos = sorted({h["stem"] for h in hits})
    rng = random.Random(args.seed)
    picked_stems = set(rng.sample(videos, min(args.n_videos, len(videos))))
    picked = []
    for h in hits:
        if h["stem"] in picked_stems and all(p["stem"] != h["stem"] for p in picked):
            picked.append(h)

    report = {
        "schema": "multi-pet-eval-set-v1",
        "selection": {
            "rule": f"coverage>={args.pet_coverage} and run>={args.pet_run}, "
            f"one interval per video, first hit, videos sampled with seed {args.seed}",
            "seed": args.seed,
            "pet_coverage": args.pet_coverage,
            "pet_run": args.pet_run,
        },
        "stats": stats,
        "n_videos_total": len(videos),
        "n_picked": len(picked),
        "picked": picked,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"stable_multi intervals = {stats['stable_multi']} (expect 565) | "
        f"videos = {len(videos)} | picked = {len(picked)} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
