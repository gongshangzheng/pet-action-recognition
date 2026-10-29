#!/usr/bin/env python3
"""运动统计 v2：用**时间窗口 + 多种统计量**重新检验「像素变动能否判在场」。

v1（`motion_vs_labels.py`）只用了「相邻两个 1 fps 抽样帧的灰度平均绝对差」——单次成对差、
间隔 1 秒，既看不到 1 秒内的动作，也无法区分「慢慢走」与「静止 + 噪声」。本脚本改成：

对每个采样点 t，按**原生帧率**解码 [t - window, t] 的连续帧，计算四类统计量：

| 指标 | 定义 | 想捕捉什么 |
|---|---|---|
| `diff_adj_max` | 相邻原生帧灰度平均绝对差的最大值 | 帧内是否有动作（哪怕只持续 1–2 帧） |
| `diff_adj_mean` | 上述差值的均值 | 持续动作强度 |
| `diff_span` | 窗首与窗尾的灰度平均绝对差 | 长时间尺度位移（慢速移动 / 位置变化） |
| `mog2_max` | MOG2 背景建模前景占比的最大值 | 与背景不同的「新物体」面积（对静止目标也有效，因为背景模型会吸收静止前景——需注意） |

同时记录 `diff_adj_p90` 作为鲁棒上限。

判定口径：标签仍用三态文件，`present = cat_present ∪ other_animal_only`。

用法（CPU 即可；4K 解码吃 CPU，务必用 remote_run 包起来）：
  python3 scripts/checks/motion_stats_windowed.py \
      --manifest results/gate/dataset_v1/manifest.csv --labels results/gate/labels_native_all_t3.jsonl \
      --video-root ~/pet-final/datasets/cat_raw/videos --out results/gate/motion_windowed.json \
      --samples 400 --window-sec 2.0 --frame-stride 2
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))]


def sweep(name: str, present: list[float], absent: list[float], target_miss: float) -> dict:
    """阈值扫描：metric ≥ 阈值 判 present；返回最优阈值与关键点。"""
    candidates = sorted({round(v, 3) for v in (present + absent)})
    if not candidates:
        return {}
    best = None
    rows = []
    for threshold in candidates[:: max(1, len(candidates) // 200)]:
        tp = sum(1 for v in present if v >= threshold)
        fp = sum(1 for v in absent if v >= threshold)
        recall = tp / max(1, len(present))
        fpr = fp / max(1, len(absent))
        rows.append((threshold, recall, fpr))
        if recall >= 1 - target_miss and (best is None or threshold > best[0]):
            best = (threshold, recall, fpr)
    # AUC（秩和法，等价于 ROC 面积）
    wins = 0.0
    for value in present:
        for other in absent:
            wins += 1.0 if value > other else (0.5 if value == other else 0.0)
    auc = wins / max(1, len(present) * len(absent))
    return {"metric": name, "auc": round(auc, 4), "best_threshold": best}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=400, help="总采样点（present/absent 各半）")
    parser.add_argument("--window-sec", type=float, default=2.0)
    parser.add_argument("--frame-stride", type=int, default=2, help="窗口内每 N 帧取一帧（降 CPU）")
    parser.add_argument("--width", type=int, default=960, help="灰度计算前的缩放宽度")
    parser.add_argument("--target-miss", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    import csv

    import cv2
    import numpy as np

    cv2.setNumThreads(2)

    labels: dict[str, str] = {}
    with args.labels.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if "label" in row:
                    labels[row["path"]] = row["label"]

    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["path"] in labels]

    present_rows = [r for r in rows if labels[r["path"]] != "absent"]
    absent_rows = [r for r in rows if labels[r["path"]] == "absent"]
    rng = random.Random(args.seed)
    half = max(50, args.samples // 2)
    picked = rng.sample(present_rows, min(half, len(present_rows))) + \
        rng.sample(absent_rows, min(half, len(absent_rows)))
    print(f"[motion-v2] 采样 {len(picked)} 点（present {min(half, len(present_rows))} / "
          f"absent {min(half, len(absent_rows))}）；窗口 {args.window_sec}s，步长 {args.frame_stride}")

    metrics = {"diff_adj_max": [], "diff_adj_mean": [], "diff_adj_p90": [], "diff_span": [], "mog2_max": []}
    truth: list[bool] = []
    per_sample = []
    backend = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=16, detectShadows=False)

    for index, row in enumerate(picked, 1):
        video = str(args.video_root / row["video"])
        frame_index = int(row["frame_idx"])
        capture = cv2.VideoCapture(video)
        if not capture.isOpened():
            continue
        fps = capture.get(cv2.CAP_PROP_FPS) or 15.0
        window_frames = int(round(args.window_sec * fps))
        start = max(0, frame_index - window_frames)
        capture.set(cv2.CAP_PROP_POS_FRAMES, float(start))
        grays, mogs = [], []
        stride = max(1, args.frame_stride)
        position = start
        while position <= frame_index:
            ok, frame = capture.read()          # 顺序读，保证时间连续（跳帧读会错位）
            if not ok:
                break
            if (position - start) % stride == 0:
                scale = args.width / frame.shape[1]
                if scale < 1.0:
                    frame = cv2.resize(frame, (args.width, int(frame.shape[0] * scale)),
                                       interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                grays.append(gray.astype(np.int16))
                mogs.append(float((backend.apply(frame) > 0).mean()))
            position += 1
        capture.release()
        if len(grays) < 3:
            continue
        diffs = [float(np.abs(grays[i] - grays[i - 1]).mean()) for i in range(1, len(grays))]
        record = {
            "path": row["path"],
            "video": row["video"],
            "frame_idx": frame_index,
            "diff_adj_max": max(diffs),
            "diff_adj_mean": float(np.mean(diffs)),
            "diff_adj_p90": float(np.percentile(diffs, 90)),
            "diff_span": float(np.abs(grays[-1] - grays[0]).mean()),
            "mog2_max": max(mogs) if mogs else 0.0,
            "present": labels[row["path"]] != "absent",
            "frames_used": len(grays),
        }
        per_sample.append(record)
        truth.append(record["present"])
        for key in metrics:
            metrics[key].append(record[key])
        if index % 50 == 0 or index == len(picked):
            print(f"[motion-v2] {index}/{len(picked)}", flush=True)

    present_mask = [i for i, flag in enumerate(truth) if flag]
    absent_mask = [i for i, flag in enumerate(truth) if not flag]
    print(f"\n有效样本 {len(truth)}：present {len(present_mask)} / absent {len(absent_mask)}")

    print("\n=== 各指标分位数（present vs absent）")
    for key, values in metrics.items():
        pv = [values[i] for i in present_mask]
        av = [values[i] for i in absent_mask]
        print(f"  {key:15s} present p50 {percentile(pv, 0.5):7.3f} / absent p50 {percentile(av, 0.5):7.3f}"
              f"   present p10 {percentile(pv, 0.1):7.3f} / absent p90 {percentile(av, 0.9):7.3f}")

    print("\n=== 阈值扫描（metric ≥ 阈值 → present）")
    results = []
    for key, values in metrics.items():
        pv = [values[i] for i in present_mask]
        av = [values[i] for i in absent_mask]
        summary = sweep(key, pv, av, args.target_miss)
        results.append(summary)
        best = summary.get("best_threshold")
        print(f"  {key:15s} AUC {summary['auc']:.3f}  最优阈值 {best[0] if best else None} "
              f"(召回 {best[1]:.3f} / 误检 {best[2]:.3f})" if best else
              f"  {key:15s} AUC {summary['auc']:.3f}  在漏检约束下无可行阈值")

    best_metric = max(results, key=lambda r: r["auc"]) if results else None
    if best_metric and best_metric.get("best_threshold"):
        key = best_metric["metric"]
        threshold = best_metric["best_threshold"][0]
        still = sum(1 for i in present_mask if metrics[key][i] < threshold)
        print(f"\n=== 用最强指标 {key}（阈值 {threshold}）时：有宠物但被判「无」的帧 "
              f"{still}/{len(present_mask)} = {still / max(1, len(present_mask)):.1%}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "samples": len(truth), "present": len(present_mask), "absent": len(absent_mask),
        "window_sec": args.window_sec, "frame_stride": args.frame_stride,
        "summary": results, "per_sample": per_sample,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n报告 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
