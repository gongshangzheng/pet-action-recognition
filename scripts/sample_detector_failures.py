#!/usr/bin/env python3
"""失效案例抽样（gdino-distill-yolo-detector 3.3）。

用途：一致率（3.2）是循环验证——学生学会教师的错误也会得高分。本脚本逐帧对比
学生与教师的框，按三类分层抽样，产出可人工看片的并排对比图。

分层：
  1. printed_or_static —— 用户人工确认过的「稳定假目标」场景（默认 charw1g 狗粮袋段），
     看学生是否把印刷金毛学成了活狗；
  2. night —— 帧平均亮度低（红外/夜视），本域历史漏检最严重；
  3. small —— 教师框面积占画幅比例最小的一批，看学生是否把小目标彻底丢掉。

对比图：左 = 教师框（绿），右 = 学生框（青），同一帧同一区域。

用法（pet 的 yolo 环境、GPU 守卫下）：
    python3 scripts/sample_detector_failures.py \
        --dataset results/pseudo_labels/gdino-v1 \
        --weights results/pseudo_labels/runs/yolo11s_1280/weights/best.pt \
        --out results/pseudo_labels/failures --per-bucket 6 --imgsz 1280
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CLASSES = ["cat", "dog"]
SMALL_AREA_RATIO = 0.01      # 占画幅比 <1% 视为小目标
NIGHT_LUMA = 60.0            # 平均亮度阈值（与历史夜视口径一致）
MATCH_IOU = 0.5


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (aa + ab - inter)


def read_labels(path: Path, w: int, h: int) -> list[tuple[int, list[float]]]:
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        p = line.split()
        cid = int(p[0])
        cx, cy, bw, bh = (float(v) for v in p[1:5])
        out.append((cid, [(cx - bw / 2) * w, (cy - bh / 2) * h,
                          (cx + bw / 2) * w, (cy + bh / 2) * h]))
    return out


def draw(img, boxes, color, prefix=""):
    vis = img.copy()
    for cid, box in boxes:
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, f"{prefix}{CLASSES[cid]}", (x1, max(12, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return vis


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-bucket", type=int, default=6)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    os.environ["OMP_NUM_THREADS"] = str(args.threads)
    torch.set_num_threads(args.threads)
    cv2.setNumThreads(args.threads)
    YOLO = importlib.import_module("ultralytics").YOLO
    model = YOLO(str(args.weights))

    manifest = json.loads((args.dataset / "dataset.json").read_text(encoding="utf-8"))
    records = manifest["records"]

    buckets: dict[str, list] = {"printed_or_static": [], "night": [], "small": []}
    for r in records:
        img_path = args.dataset / r["image"]
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        teacher = read_labels(args.dataset / r["label"], w, h)
        luma = float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())
        frame_area = w * h
        small = any((b[2] - b[0]) * (b[3] - b[1]) / frame_area < SMALL_AREA_RATIO for _, b in teacher)
        entry = {"record": r, "img": img, "teacher": teacher, "luma": luma}
        if "charw1g" in r["video"]:
            buckets["printed_or_static"].append(entry)
        if luma < NIGHT_LUMA:
            buckets["night"].append(entry)
        if small:
            buckets["small"].append(entry)

    args.out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for bucket, entries in buckets.items():
        if not entries:
            summary[bucket] = {"samples": 0}
            continue
        step = max(1, len(entries) // args.per_bucket)
        picked = entries[::step][: args.per_bucket]
        rows = []
        for i, e in enumerate(picked):
            res = model.predict(e["img"], imgsz=args.imgsz, device=args.device,
                                conf=args.conf, verbose=False)[0]
            h, w = e["img"].shape[:2]
            student = []
            if res.boxes is not None and len(res.boxes):
                for cls_id, xyxy in zip(res.boxes.cls.tolist(), res.boxes.xyxy.tolist(), strict=True):
                    student.append((int(cls_id), xyxy))

            matched = sum(1 for _, tb in e["teacher"]
                          if any(iou(tb, sb) >= MATCH_IOU for _, sb in student))
            left = draw(e["img"], e["teacher"], (0, 200, 0), "T:")
            right = draw(e["img"], student, (255, 200, 0), "S:")
            canvas = np.hstack([left, right])
            name = f"{bucket}_{i:02d}_{Path(e['record']['image']).stem}.jpg"
            cv2.imwrite(str(args.out / name), canvas)
            rows.append({
                "image": e["record"]["image"],
                "frame": e["record"]["frame"],
                "luma": round(e["luma"], 1),
                "teacher_boxes": len(e["teacher"]),
                "student_boxes": len(student),
                "matched": matched,
                "missed": len(e["teacher"]) - matched,
                "overlay": name,
            })
        summary[bucket] = {"samples": len(rows), "rows": rows}
        print(f"[{bucket}] {len(rows)} 帧，教师框共 {sum(r['teacher_boxes'] for r in rows)}，"
              f"学生框共 {sum(r['student_boxes'] for r in rows)}，漏 {sum(r['missed'] for r in rows)}",
              flush=True)

    (args.out / "summary.json").write_text(
        json.dumps({"schema": "detector-failure-samples-v1",
                    "weights": str(args.weights), "imgsz": args.imgsz,
                    "conf": args.conf, "buckets": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"SAMPLES DONE -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
