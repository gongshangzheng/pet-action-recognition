#!/usr/bin/env python3
"""伪标签导出（gdino-distill-yolo-detector 1.1）。

把 GroundingDINO 检测缓存转成 YOLO 训练格式，并记录完整回溯信息。

过滤（design 4.2，**不设置信度下限**——实测真猫置信 0.331 低于三条误检的 0.502/0.536/0.616，
任何置信度截断都会先杀掉真猫）：
  1. IoS ≥ 0.8 的嵌套重复（交集/较小框面积，跨物种），保留置信度高者；
  2. 退化框：相对最大框的面积比 < 0.15 或 > 3；
  3. 单帧候选数 > 20（异常帧，整帧跳过并记录）。

产物：
  <out>/images/<video>__f<frame>.jpg    长边缩放到 --long-side（与训练 imgsz 对齐）
  <out>/labels/<video>__f<frame>.txt    YOLO 格式（cat=0, dog=1）
  <out>/classes.txt
  <out>/dataset.json                    回溯清单：每图 → 源视频/帧号/缓存指纹/教师指纹
  <out>/drops.jsonl                     逐帧丢弃明细

用法（在 pet 上执行，视频与缓存都在那边）：
    python3 scripts/export_pseudo_labels.py \
        --detections-dir results/cat_crop_classification/gdino-crop-20261103a/assets/full_run/detections \
        --video-root /home/wyy/pet-final-v1/datasets/cat_raw \
        --out results/pseudo_labels/gdino-v1 --max-frames-per-video 8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from petlib.schemas import Detection  # noqa: E402
from petlib.tracking.anchors import DEDUP_IOS_MIN, dedup_nested  # noqa: E402

CLASSES = ["cat", "dog"]
CLASS_ID = {name: i for i, name in enumerate(CLASSES)}
DETECTION_CACHE_SCHEMA = "cat-crop-detection-v2"
MAX_CANDIDATES_PER_FRAME = 20
AREA_RATIO_MIN = 0.15
AREA_RATIO_MAX = 3.0
SCHEMA = "pseudo-label-dataset-v1"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def box_area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def filter_candidates(state: dict) -> tuple[list[dict], list[dict]]:
    """返回 (保留的原始候选, 丢弃明细)。顺序：异常帧 → IoS 去重 → 退化框。"""
    raw = list(state.get("cat_candidates", [])) + list(state.get("dog_candidates", []))
    if len(raw) > MAX_CANDIDATES_PER_FRAME:
        return [], [{"reason": "too_many_candidates", "n_candidates": len(raw)}]

    dets = [
        Detection(frame=0, box=(float(c["box"][0]), float(c["box"][1]),
                                float(c["box"][2]), float(c["box"][3])),
                  conf=float(c["confidence"]), cls=c["class"])
        for c in raw
    ]
    kept_dets, nested_log = dedup_nested(dets, 0)
    drops = [{"reason": "nested_duplicate", **entry} for entry in nested_log]

    if not kept_dets:
        return [], drops
    primary_area = max(box_area(d.box) for d in kept_dets)
    kept: list[dict] = []
    for d in kept_dets:
        ratio = box_area(d.box) / primary_area if primary_area else 0.0
        if ratio < AREA_RATIO_MIN or ratio > AREA_RATIO_MAX:
            drops.append({"reason": "degenerate_area",
                          "dropped_class": d.cls,
                          "dropped_box": [round(v, 1) for v in d.box],
                          "area_ratio": round(ratio, 4)})
            continue
        kept.append({"class": d.cls, "box": list(d.box), "confidence": d.conf})
    return kept, drops


def to_yolo_line(item: dict, width: int, height: int) -> str | None:
    if item["class"] not in CLASS_ID:
        return None
    x1, y1, x2, y2 = item["box"]
    cx, cy = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
    w, h = (x2 - x1) / width, (y2 - y1) / height
    if w <= 0 or h <= 0:
        return None
    return f"{CLASS_ID[item['class']]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def split_of(stem: str, rng_seed: int, val_ratio: float, test_ratio: float) -> str:
    """按源视频划分：对视频名做稳定哈希，保证同一视频永远落同一 split。"""
    bucket = int(hashlib.sha256(f"{rng_seed}:{stem}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    if bucket < test_ratio:
        return "test"
    if bucket < test_ratio + val_ratio:
        return "val"
    return "train"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--detections-dir", type=Path, required=True)
    ap.add_argument("--video-root", type=Path, required=True, help="含 videos/ 子目录的根")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-frames-per-video", type=int, default=8)
    ap.add_argument("--long-side", type=int, default=1280)
    ap.add_argument("--jpeg-quality", type=int, default=90)
    ap.add_argument("--seed", type=int, default=20261107)
    ap.add_argument("--val-ratio", type=float, default=0.1)
    ap.add_argument("--test-ratio", type=float, default=0.1)
    args = ap.parse_args()

    caches = sorted(args.detections_dir.glob("*.json"))
    if not caches:
        raise FileNotFoundError(f"no detection caches in {args.detections_dir}")

    # 前置指纹校验：教师指纹不一致时立刻退出，不留半成品
    pre_fps = {}
    for cache_path in caches:
        p = json.loads(cache_path.read_text(encoding="utf-8"))
        if p.get("schema") != DETECTION_CACHE_SCHEMA:
            raise ValueError(f"{cache_path}: unexpected schema {p.get('schema')}")
        pre_fps.setdefault(sha256_text(json.dumps(p["fingerprint"], sort_keys=True, ensure_ascii=False)),
                           []).append(cache_path.name)
    if len(pre_fps) > 1:
        detail = {k[:12]: v[:3] for k, v in pre_fps.items()}
        raise ValueError(f"教师指纹不一致：发现 {len(pre_fps)} 种，拒绝混合导出 {detail}")

    (args.out / "images").mkdir(parents=True, exist_ok=True)
    (args.out / "labels").mkdir(parents=True, exist_ok=True)
    (args.out / "classes.txt").write_text("\n".join(CLASSES) + "\n", encoding="utf-8")

    records: list[dict] = []
    drops_fh = (args.out / "drops.jsonl").open("w", encoding="utf-8")
    fingerprints: set[str] = set()
    skipped_videos: list[str] = []
    total_frames = total_boxes = 0

    for cache_path in caches:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("schema") != DETECTION_CACHE_SCHEMA:
            raise ValueError(f"{cache_path}: unexpected schema {payload.get('schema')}")
        fp = json.dumps(payload["fingerprint"], sort_keys=True, ensure_ascii=False)
        fingerprints.add(sha256_text(fp))
        teacher_fp = sha256_text(fp)

        stem = Path(payload["video"]).stem
        video_path = args.video_root / "videos" / f"{stem}.mp4"
        if not video_path.is_file():
            skipped_videos.append(stem)
            continue

        anchors = sorted((int(k), v) for k, v in payload["anchors"].items())
        rng = random.Random(f"{args.seed}:{stem}")
        picked = sorted(rng.sample(anchors, min(args.max_frames_per_video, len(anchors))))

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            skipped_videos.append(stem)
            continue
        for frame_idx, state in picked:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, img = cap.read()
            if not ok:
                continue
            h, w = img.shape[:2]
            scale = args.long_side / max(w, h)
            if scale < 1.0:
                img = cv2.resize(img, (int(round(w * scale)), int(round(h * scale))),
                                 interpolation=cv2.INTER_AREA)
            kept, drops = filter_candidates(state)
            name = f"{stem}__f{frame_idx:06d}"
            cv2.imwrite(str(args.out / "images" / f"{name}.jpg"), img,
                        [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])

            # 归一化用原始帧尺寸：图像等比缩放，框坐标也等比，比例不变
            lines = [ln for item in kept if (ln := to_yolo_line(item, w, h))]
            (args.out / "labels" / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

            if drops:
                drops_fh.write(json.dumps({"image": name, "frame": frame_idx, "drops": drops},
                                          ensure_ascii=False) + "\n")

            total_frames += 1
            total_boxes += len(lines)
            records.append({
                "image": f"images/{name}.jpg",
                "label": f"labels/{name}.txt",
                "video": f"videos/{stem}.mp4",
                "frame": frame_idx,
                "detection_cache": cache_path.name,
                "teacher_fingerprint": teacher_fp,
                "split": split_of(stem, args.seed, args.val_ratio, args.test_ratio),
                "n_boxes": len(lines),
                "n_dropped": len(drops),
                "image_wh": [int(img.shape[1]), int(img.shape[0])],
                "source_wh": [w, h],
            })
        cap.release()
    drops_fh.close()

    if len(fingerprints) > 1:
        raise ValueError(f"教师指纹不一致：发现 {len(fingerprints)} 种，拒绝混合导出")

    manifest = {
        "schema": SCHEMA,
        "teacher_fingerprint": next(iter(fingerprints)),
        "teacher_fingerprint_kind": "sha256 of fingerprint json",
        "params": {
            "dedup_ios_min": DEDUP_IOS_MIN,
            "max_candidates_per_frame": MAX_CANDIDATES_PER_FRAME,
            "area_ratio_min": AREA_RATIO_MIN,
            "area_ratio_max": AREA_RATIO_MAX,
            "max_frames_per_video": args.max_frames_per_video,
            "long_side": args.long_side,
            "jpeg_quality": args.jpeg_quality,
            "seed": args.seed,
            "val_ratio": args.val_ratio,
            "test_ratio": args.test_ratio,
        },
        "classes": CLASSES,
        "stats": {
            "videos": len(caches) - len(skipped_videos),
            "skipped_videos": len(skipped_videos),
            "frames": total_frames,
            "boxes": total_boxes,
            "boxes_per_frame": round(total_boxes / max(1, total_frames), 3),
        },
        "records": records,
    }
    (args.out / "dataset.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    if skipped_videos:
        (args.out / "skipped_videos.txt").write_text("\n".join(skipped_videos) + "\n", encoding="utf-8")

    print(json.dumps(manifest["stats"], ensure_ascii=False))
    print(f"EXPORT DONE -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
