#!/usr/bin/env python3
"""门控标签分析：三态分布 / 猫框相对面积 / 阈值重标定 / dog-only 灰带。

用途：回答两个分辨率问题（不是同一个问题）——
  ① **教师标注**需要多清晰才判得准？（本脚本给出 dog-only 灰带、阈值重标定后的三态分布）
  ② **门控模型**输入最小要多少像素？（本脚本给出猫框相对面积的百分位 → 换算到目标输入尺寸后的边长）

用法：
  python3 scripts/checks/analyze_gate_labels.py \
      --labels results/gate/labels_native_full_t3.jsonl \
      --manifest results/gate/dataset_v1/manifest.csv \
      --thresholds 0.10 0.15 0.20 0.30 0.50
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None, help="可选：用于按 domain/split 分组")
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.10, 0.15, 0.20, 0.30, 0.50])
    parser.add_argument("--dog-strong", type=float, default=0.30)
    parser.add_argument("--cat-weak", type=float, default=0.15)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    meta: dict[str, dict] = {}
    if args.manifest and args.manifest.is_file():
        with args.manifest.open(encoding="utf-8", newline="") as stream:
            meta = {row["path"]: row for row in csv.DictReader(stream)}

    records = []
    with args.labels.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            if "error" in row:
                continue
            info = meta.get(row["path"], {})
            records.append({**row, "domain": info.get("domain", "?"), "split": info.get("split", "?")})

    total = len(records)
    print(f"有效记录 {total} 帧（跳过出错行）")

    # 1) 猫框相对面积 → 换算到目标输入尺寸后的边长
    ratios: dict[str, list[float]] = defaultdict(list)
    for row in records:
        box = row.get("box_cat")
        width, height = row.get("native_width"), row.get("native_height")
        if not box or not width or not height:
            continue
        area = max(0.0, (box[2] - box[0])) * max(0.0, (box[3] - box[1]))
        ratios[row["domain"]].append(area / float(width * height))
    print("\n=== 猫框占画面面积比（决定模型输入分辨率）")
    for domain, values in sorted(ratios.items()):
        p10, p50, p90 = percentile(values, 0.1), percentile(values, 0.5), percentile(values, 0.9)
        print(f"  {domain:6s} n={len(values):5d}  p10 {p10:.5f}  p50 {p50:.5f}  p90 {p90:.5f}")
        for target in (448, 640, 960, 1280):
            # 面积比 → 在该输入下猫框短边像素（按 16:9 画面短边 = target 估算）
            side = (p50 ** 0.5) * target
            print(f"      输入短边 {target:4d} → 中位猫框约 {side:5.1f} px 边长")

    # 2) 阈值重标定
    print("\n=== 阈值重标定（cat 分数）")
    for threshold in args.thresholds:
        cat = sum(1 for row in records if (row.get("score_cat") or 0) >= threshold)
        dog_only = sum(1 for row in records
                       if (row.get("score_cat") or 0) < threshold and (row.get("score_dog") or 0) >= threshold)
        print(f"  cat>={threshold:.2f}: cat {cat:6d} ({cat / total:.1%})  dog-only {dog_only:6d} "
              f"({dog_only / total:.1%})  absent {total - cat - dog_only:6d}")

    # 3) dog-only 灰带：dog 强、cat 弱 → 很可能是「猫被判成狗」
    strong_dog = [row for row in records
                  if (row.get("score_dog") or 0) >= args.dog_strong and (row.get("score_cat") or 0) < args.cat_weak]
    grey = [row for row in records
            if args.cat_weak <= (row.get("score_cat") or 0) < 0.30]
    print(f"\n=== dog 强而 cat 弱（dog≥{args.dog_strong}, cat<{args.cat_weak}）：{len(strong_dog)} 帧"
          f"（{len(strong_dog) / total:.1%}）→ 建议放大复核")
    print(f"=== cat 灰带（{args.cat_weak} ≤ cat < 0.30）：{len(grey)} 帧 → 阈值选择的敏感区")

    # 4) 三态 × 域
    print("\n=== 三态分布（按域）")
    table: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in records:
        table[(row["domain"], row["split"])][row.get("label", "?")] += 1
    for key in sorted(table):
        counter = table[key]
        n = sum(counter.values())
        print(f"  {key[0]:6s}/{key[1]:5s} n={n:5d} cat {counter['cat_present']:5d} "
              f"dog-only {counter['other_animal_only']:4d} absent {counter['absent']:5d}")

    if args.json_out:
        args.json_out.write_text(json.dumps({
            "total": total,
            "cat_area_ratio": {k: {"p10": percentile(v, 0.1), "p50": percentile(v, 0.5), "p90": percentile(v, 0.9)}
                               for k, v in ratios.items()},
            "dog_strong_cat_weak": len(strong_dog),
            "cat_grey_band": len(grey),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
