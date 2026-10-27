#!/usr/bin/env python3
"""门控输入分辨率标定：同一教师/候选在多个输入尺寸下的检出率与延迟曲线。

D11 实测已证明"越小越省"不成立（猫在 2880×1620 广角里像素预算很小）。
本脚本给出「输入尺寸 → 检出率 / 单帧延迟 / 显存」曲线，用来定最小可用分辨率。

以最大尺寸的判定作为相对召回基准（不是绝对真值——绝对真值靠人工核验集）。

用法（GPU 推荐；CPU 也可但慢）：
  python scripts/checks/calibrate_gate_resolution.py \
      --manifest results/gate/subset_400.csv --image-root results/gate/dataset_v1 \
      --weights ~/pet-final/weights/yolo11n.pt --sizes 256 384 512 640 960 1280 \
      --out results/gate/calibration_yolo.jsonl --device cuda:0
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", default=[256, 384, 512, 640, 960, 1280])
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--conf", type=float, default=0.05)
    parser.add_argument("--cat-class", type=int, default=15)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    from ultralytics import YOLO

    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    paths = [str(args.image_root / row["path"]) for row in rows]
    model = YOLO(str(args.weights))

    results = []
    per_size: dict[int, dict[str, float]] = {}
    for size in args.sizes:
        started = time.time()
        scores: dict[str, float] = {}
        for index in range(0, len(paths), args.batch):
            chunk = paths[index:index + args.batch]
            predictions = model.predict(chunk, imgsz=size, conf=args.conf, verbose=False, device=args.device)
            for path, prediction in zip(chunk, predictions):
                best = 0.0
                boxes = prediction.boxes
                if boxes is not None and len(boxes):
                    for box_score, cls in zip(boxes.conf.tolist(), boxes.cls.tolist()):
                        if int(cls) == args.cat_class and float(box_score) > best:
                            best = float(box_score)
                scores[path] = best
        elapsed = time.time() - started
        hits = sum(1 for value in scores.values() if value >= args.threshold)
        per_size[size] = {"hits": hits, "seconds": elapsed, "ms_per_frame": 1000 * elapsed / max(1, len(paths))}
        for path, score in scores.items():
            results.append({"size": size, "path": path, "score": round(score, 4)})
        print(f"[calibrate] imgsz={size:5d} 检出 {hits}/{len(paths)} "
              f"({hits / max(1, len(paths)):.1%})  单帧 {per_size[size]['ms_per_frame']:.1f} ms", flush=True)

    reference_size = max(args.sizes)
    reference = {r["path"] for r in results if r["size"] == reference_size and r["score"] >= args.threshold}
    summary = []
    for size in args.sizes:
        hits = {r["path"] for r in results if r["size"] == size and r["score"] >= args.threshold}
        recall_vs_ref = len(hits & reference) / max(1, len(reference))
        summary.append({
            "imgsz": size,
            "hits": len(hits),
            "recall_vs_max_size": round(recall_vs_ref, 4),
            "ms_per_frame": round(per_size[size]["ms_per_frame"], 2),
        })
        print(f"[calibrate] imgsz={size:5d} 相对召回(基准 imgsz={reference_size}) {recall_vs_ref:.1%}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as stream:
        for row in results:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps({"reference_size": reference_size, "table": summary,
                                        "threshold": args.threshold, "manifest": str(args.manifest)},
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[calibrate] 明细 → {args.out}；汇总 → {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
