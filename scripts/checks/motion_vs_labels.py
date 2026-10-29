#!/usr/bin/env python3
"""零成本对照：帧间像素变动（运动能量）能不能替代模型判断「有没有宠物」？

用途：回答「门控能不能不用模型，只看画面变动」。做法是拿已有的帧级标签当参照，
把每帧与前一个抽样帧（1 秒前）做灰度平均绝对差，看这个纯像素指标与标签的重合度。

输出：
  - present / absent 两组的运动能量分位数
  - 阈值扫描：在「漏检 ≤ 目标」下能取到的最高阈值，及对应误检率（"没宠物却触发了"）
  - 关键盲点量化：**有宠物但运动能量极低**的帧占比（= 静止的猫，本项目最常见的状态）
  - 反向误触发：无宠物但运动能量高（红外切换 / 曝光变化 / 窗帘）

用法（CPU 即可，不需要 GPU）：
  python3 scripts/checks/motion_vs_labels.py \
      --manifest results/gate/dataset_v1/manifest.csv \
      --labels results/gate/labels_native_all_t3.jsonl \
      --image-root results/gate/dataset_v1 --out results/gate/motion_probe.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target-miss", type=float, default=0.02)
    parser.add_argument("--still-threshold", type=float, default=2.0,
                        help="低于该运动能量视为「画面几乎没有动」（默认 2.0 灰度级）")
    args = parser.parse_args()

    import csv
    import numpy as np
    from PIL import Image

    labels = {}
    with args.labels.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if "label" in row:
                    labels[row["path"]] = row["label"]

    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_video[row["video"]].append(row)
    for video in by_video:
        by_video[video].sort(key=lambda r: int(r["frame_idx"]))

    samples = []  # (motion, is_present, path)
    missing = 0
    for video, group in by_video.items():
        previous = None
        for row in group:
            try:
                gray = np.asarray(Image.open(args.image_root / row["path"]).convert("L"), dtype=np.int16)
            except Exception:
                missing += 1
                previous = None
                continue
            if previous is not None and previous.shape == gray.shape:
                motion = float(np.abs(gray - previous).mean())
                label = labels.get(row["path"])
                if label is not None:
                    samples.append((motion, label in ("cat_present", "other_animal_only"), row["path"]))
            previous = gray

    present = [m for m, p, _ in samples if p]
    absent = [m for m, p, _ in samples if not p]
    print(f"可比对帧 {len(samples)}（缺标签或解码失败 {missing}）；present {len(present)} / absent {len(absent)}")

    print("\n=== 运动能量（灰度平均绝对差，1 秒间隔）分位数")
    for name, values in (("present", present), ("absent", absent)):
        if not values:
            continue
        print(f"  {name:8s} n={len(values):6d}  p10 {percentile(values,0.1):6.2f}  "
              f"p50 {percentile(values,0.5):6.2f}  p90 {percentile(values,0.9):6.2f}  "
              f"p99 {percentile(values,0.99):6.2f}")

    # 阈值扫描：运动 ≥ 阈值 判 present
    thresholds = sorted({round(t, 2) for t in
                         [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, 50]})
    print("\n=== 阈值扫描（motion ≥ 阈值 → 判「有宠物」）")
    print("  阈值   召回   漏检   误检率(absent 被判 present)")
    best = None
    for threshold in thresholds:
        tp = sum(1 for m in present if m >= threshold)
        fn = len(present) - tp
        fp = sum(1 for m in absent if m >= threshold)
        recall = tp / max(1, len(present))
        fpr = fp / max(1, len(absent))
        flag = ""
        if recall >= 1 - args.target_miss:
            best = (threshold, recall, fpr)
            flag = "  ← 满足漏检约束里阈值最高"
        print(f"  {threshold:5.1f}  {recall:5.3f}  {fn:5d}  {fpr:6.3f}{flag}")

    still_present = sum(1 for m in present if m < args.still_threshold)
    print(f"\n=== 关键盲点：有宠物但运动能量 < {args.still_threshold} 的帧 "
          f"{still_present}/{len(present)} = {still_present / max(1, len(present)):.1%}")
    print("    （这些是静止/趴卧的猫——纯运动检测会整段漏掉，而 prolonged_stationary 是本项目最多的标注之一）")
    noisy_absent = sum(1 for m in absent if m >= 5.0)
    print(f"=== 反向误触发：无宠物但运动能量 ≥ 5 的帧 {noisy_absent}/{len(absent)} = "
          f"{noisy_absent / max(1, len(absent)):.1%}（红外切换 / 曝光 / 窗帘）")

    report = {
        "samples": len(samples), "present": len(present), "absent": len(absent),
        "percentiles": {name: {"p10": percentile(v, 0.1), "p50": percentile(v, 0.5),
                               "p90": percentile(v, 0.9), "p99": percentile(v, 0.99)}
                        for name, v in (("present", present), ("absent", absent))},
        "best_threshold": best,
        "still_present_ratio": still_present / max(1, len(present)),
        "absent_high_motion_ratio": noisy_absent / max(1, len(absent)),
        "still_threshold": args.still_threshold,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n报告 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
