#!/usr/bin/env python3
"""框细化探针（multi-pet-sort-tracking 4.1）：MobileSAM vs SAM2-small 对照。

方法（design 4.10「先裁后分」）：把候选框向外扩 pad 后裁出，只把这块裁剪图送进分割模型，
box prompt 用框在裁剪图内的坐标；填充率 = (mask ∩ 框) / 框面积，紧框接近 1、松框明显偏低。

用法（在 pet 的 yolo 环境跑，模型代码与权重在仓库外）：
    python3 scripts/probe_box_refinement.py \
        --cases cases.json --out results/tracking_stride2/refine_probe \
        --mobile-sam-dir /home/wyy/models/sam/MobileSAM \
        --mobile-sam-ckpt /home/wyy/models/sam/MobileSAM/weights/mobile_sam.pt \
        --sam2-dir /home/wyy/models/sam/sam2 \
        --sam2-ckpt /home/wyy/models/sam/sam2_hiera_small.pt

cases.json 结构：[{"id": "...", "video": "/abs/path.mp4", "frame": 185,
                  "box": [x1, y1, x2, y2], "note": "..."}]
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PAD_RATIO = 0.15


def expand_box(box, w, h, pad=PAD_RATIO):
    x1, y1, x2, y2 = box
    pw, ph = (x2 - x1) * pad, (y2 - y1) * pad
    return (
        int(max(0, x1 - pw)), int(max(0, y1 - ph)),
        int(min(w, x2 + pw)), int(min(h, y2 + ph)),
    )


def fill_ratio(mask: np.ndarray, box_in_crop) -> float:
    """mask 落在框内的面积 / 框面积。"""
    x1, y1, x2, y2 = box_in_crop
    area = max(1, (x2 - x1) * (y2 - y1))
    sub = mask[int(y1):int(y2), int(x1):int(x2)]
    return float(sub.sum()) / area


def mask_box_iou(mask: np.ndarray, box_in_crop) -> float | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    mb = (xs.min(), ys.min(), xs.max(), ys.max())
    bx1, by1, bx2, by2 = box_in_crop
    ix1, iy1 = max(mb[0], bx1), max(mb[1], by1)
    ix2, iy2 = min(mb[2], bx2), min(mb[3], by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_m = (mb[2] - mb[0]) * (mb[3] - mb[1])
    area_b = (bx2 - bx1) * (by2 - by1)
    return float(inter) / float(area_m + area_b - inter)


def read_frame(video: Path, frame: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, img = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read frame {frame} of {video}")
    return img


def save_overlay(crop, box_in_crop, mask, path: Path) -> None:
    vis = crop.copy()
    if mask is not None:
        vis[mask] = (0.35 * vis[mask] + 0.65 * np.array([0, 0, 255])).astype(np.uint8)
    x1, y1, x2, y2 = [int(v) for v in box_in_crop]
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.imwrite(str(path), vis)


def build_mobile_sam(model_dir: Path, ckpt: Path):
    """模型代码只在目标机器（仓库外）存在，因此用 importlib 动态导入。"""
    sys.path.insert(0, str(model_dir))
    module = importlib.import_module("mobile_sam")
    sam = module.sam_model_registry["vit_t"](checkpoint=str(ckpt))
    sam.eval()
    return module.SamPredictor(sam)


def build_sam2(model_dir: Path, ckpt: Path):
    sys.path.insert(0, str(model_dir))
    build = importlib.import_module("sam2.build_sam")
    predictor_mod = importlib.import_module("sam2.sam2_image_predictor")
    model = build.build_sam2("configs/sam2/sam2_hiera_s.yaml", str(ckpt))
    model.eval()
    return predictor_mod.SAM2ImagePredictor(model)


def run_case(predictor, kind: str, crop: np.ndarray, box_in_crop, out_png: Path) -> dict:
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    predictor.set_image(rgb)
    box = np.array([box_in_crop], dtype=np.float32)
    masks, scores, _ = predictor.predict(box=box, multimask_output=False)
    mask = masks[0].astype(bool)
    save_overlay(crop, box_in_crop, mask, out_png)
    iou = mask_box_iou(mask, box_in_crop)
    return {
        "model": kind,
        "fill_ratio": round(fill_ratio(mask, box_in_crop), 4),
        "mask_box_iou": None if iou is None else round(iou, 4),
        "score": round(float(scores[0]), 4),
        "overlay": out_png.name,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mobile-sam-dir", type=Path, required=True)
    ap.add_argument("--mobile-sam-ckpt", type=Path, required=True)
    ap.add_argument("--sam2-dir", type=Path, required=True)
    ap.add_argument("--sam2-ckpt", type=Path, required=True)
    args = ap.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "overlays").mkdir(exist_ok=True)

    mobile = build_mobile_sam(args.mobile_sam_dir, args.mobile_sam_ckpt)
    sam2 = build_sam2(args.sam2_dir, args.sam2_ckpt)

    rows = []
    for case in cases:
        img = read_frame(Path(case["video"]), int(case["frame"]))
        h, w = img.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in case["box"]]
        cx1, cy1, cx2, cy2 = expand_box((x1, y1, x2, y2), w, h)
        crop = img[cy1:cy2, cx1:cx2]
        box_in_crop = (x1 - cx1, y1 - cy1, x2 - cx1, y2 - cy1)
        row = {
            "id": case["id"],
            "note": case.get("note", ""),
            "box_wh": [x2 - x1, y2 - y1],
            "results": [],
        }
        for kind, predictor in (("mobile_sam", mobile), ("sam2_small", sam2)):
            png = args.out / "overlays" / f"{case['id']}__{kind}.png"
            res = run_case(predictor, kind, crop, box_in_crop, png)
            row["results"].append(res)
        rows.append(row)
        print(f"[probe] {case['id']}: " + " | ".join(
            f"{r['model']} fill={r['fill_ratio']}" for r in row["results"]), flush=True)

    (args.out / "probe.json").write_text(
        json.dumps({"schema": "box-refine-probe-v1", "pad_ratio": PAD_RATIO, "cases": rows},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PROBE DONE -> {args.out}/probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
