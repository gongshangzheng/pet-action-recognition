#!/usr/bin/env python3
"""原生分辨率 GroundingDINO 标注：直接从源视频解出指定帧，按最高可用清晰度推理，输出三态标签。

为什么不用已落盘的 1280 帧：`prepare_gate_frames.py` 存的是长边 1280（720p）的整帧，
而源视频是 2880×1620；GroundingDINO 的默认处理器又会把短边压到 800 —— 小猫在两步降采样里会消失
（D11 已实测 640 输入系统性漏检）。本脚本因此：

1. 按 manifest 的 `video` + `frame_idx` 从源视频**解出原始分辨率帧**（不落盘，省磁盘）；
2. GDINO 处理器短边可调（`--shortest-edge` / `--max-size`），或 **2×2 分块推理**（`--tiles 2`）——
   分块等价于把有效分辨率再放大一倍，是补小猫的标准做法；
3. 输出三态：`cat_present` / `other_animal_only` / `absent`（prompt 默认 `cat. dog.`），
   同时保留每个类别的分数与框，便于后续审计。

用法（GPU）：
  # 先在一个小子集上把分辨率/分块参数定下来
  python scripts/label_gate_native.py --manifest results/gate/subset_400.csv \
      --video-root ~/pet-final/datasets/cat_raw/videos --out results/gate/labels_native_subset.jsonl \
      --shortest-edge 1333 --max-size 2400 --tiles 2 --device cuda:0

  # 全量
  python scripts/label_gate_native.py --manifest results/gate/dataset_v1/manifest.csv \
      --video-root ~/pet-final/datasets/cat_raw/videos --out results/gate/labels_native.jsonl \
      --shortest-edge 1333 --max-size 2400 --tiles 2 --device cuda:0
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def label_from_scores(cat: float, dog: float, threshold: float) -> str:
    if cat >= threshold:
        return "cat_present"
    if dog >= threshold:
        return "other_animal_only"
    return "absent"


def run_tiles(model, processor, image, args) -> tuple[dict[str, float], dict[str, list[float]]]:
    """整图或 2×2 分块推理，返回每类的最高分与对应框（坐标已换算回原图）。"""
    import torch

    width, height = image.size
    grids = [(0, 0, width, height)]
    if args.tiles == 2:
        overlap = 0.1
        half_w, half_h = width / 2, height / 2
        pad_w, pad_h = half_w * overlap, half_h * overlap
        grids = []
        for row in (0, 1):
            for col in (0, 1):
                x1 = max(0, int(col * half_w - pad_w))
                y1 = max(0, int(row * half_h - pad_h))
                x2 = min(width, int((col + 1) * half_w + pad_w))
                y2 = min(height, int((row + 1) * half_h + pad_h))
                grids.append((x1, y1, x2, y2))

    best: dict[str, float] = {}
    best_box: dict[str, list[float]] = {}
    for x1, y1, x2, y2 in grids:
        crop = image.crop((x1, y1, x2, y2))
        inputs = processor(images=crop, text=args.prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            outputs = model(**inputs)
        result = processor.post_process_grounded_object_detection(
            outputs, inputs["input_ids"], threshold=args.threshold,
            text_threshold=args.text_threshold, target_sizes=[crop.size[::-1]])[0]
        texts = result.get("labels") or result.get("text_labels") or []
        for position, (box, score) in enumerate(zip(result["boxes"].tolist(), result["scores"].tolist())):
            label = str(texts[position]) if position < len(texts) else "cat"
            label = label.strip().rstrip(".").lower()
            if float(score) > best.get(label, 0.0):
                best[label] = float(score)
                best_box[label] = [round(box[0] + x1, 1), round(box[1] + y1, 1),
                                   round(box[2] + x1, 1), round(box[3] + y1, 1)]
    return best, best_box


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default="IDEA-Research/grounding-dino-tiny")
    parser.add_argument("--prompt", default="cat. dog.")
    parser.add_argument("--threshold", type=float, default=0.20, help="三态判定阈值（低于此分数视为无该宠物）")
    parser.add_argument("--detect-threshold", type=float, default=0.05, help="检测框保留阈值（便于事后重标定）")
    parser.add_argument("--text-threshold", type=float, default=0.15)
    parser.add_argument("--shortest-edge", type=int, default=1333, help="GDINO 处理器短边（默认 1333，高于官方 800）")
    parser.add_argument("--max-size", type=int, default=2400)
    parser.add_argument("--tiles", type=int, choices=[1, 2], default=1, help="2 = 2×2 分块（提高有效分辨率）")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条（调试）")
    parser.add_argument("--save-crops", type=Path, default=None, help="可选：把解出的原始分辨率帧另存（仅供抽检）")
    args = parser.parse_args()

    import decord
    import torch
    from PIL import Image
    from transformers import AutoProcessor, GroundingDinoForObjectDetection

    processor = AutoProcessor.from_pretrained(args.model_id)
    # transformers 4.49 的 GroundingDinoImageProcessor.size 是双键 dict
    #   {'shortest_edge': 800, 'longest_edge': 1333}
    # 只写 shortest_edge（漏 longest_edge）会让内部 resize 计算异常并 segfault（实测 exit 139），
    # 因此两键必须一起给；max_size 属性不参与这条路径，不要单独赋值。
    processor.image_processor.size = {"shortest_edge": args.shortest_edge, "longest_edge": args.max_size}
    model = GroundingDinoForObjectDetection.from_pretrained(args.model_id).to(args.device).eval()

    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if args.limit:
        rows = rows[: args.limit]

    readers: dict[str, object] = {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    counts = {"cat_present": 0, "other_animal_only": 0, "absent": 0}
    with args.out.open("w", encoding="utf-8") as out_stream:
        for index, row in enumerate(rows, 1):
            video = str(args.video_root / row["video"])
            frame_index = int(row["frame_idx"])
            try:
                reader = readers.get(video)
                if reader is None:
                    reader = decord.VideoReader(video, num_threads=1)
                    readers[video] = reader
                frame = reader[frame_index].asnumpy()
            except Exception as error:
                out_stream.write(json.dumps({"path": row["path"], "error": f"{type(error).__name__}: {error}"},
                                            ensure_ascii=False) + "\n")
                continue
            image = Image.fromarray(frame)
            if args.save_crops:
                args.save_crops.mkdir(parents=True, exist_ok=True)
                target = args.save_crops / Path(row["path"]).name
                image.save(target, quality=92)
            best, best_box = run_tiles(model, processor, image, args)
            cat_score, dog_score = best.get("cat", 0.0), best.get("dog", 0.0)
            label = label_from_scores(cat_score, dog_score, args.threshold)
            counts[label] += 1
            out_stream.write(json.dumps({
                "path": row["path"], "video": row["video"], "frame_idx": frame_index,
                "native_width": image.size[0], "native_height": image.size[1],
                "label": label, "score_cat": round(cat_score, 4), "score_dog": round(dog_score, 4),
                "box_cat": best_box.get("cat"), "box_dog": best_box.get("dog"),
                "per_class": {k: round(v, 4) for k, v in sorted(best.items())},
                "teacher": "gdino_native", "tiles": args.tiles, "shortest_edge": args.shortest_edge,
            }, ensure_ascii=False) + "\n")
            if index % 25 == 0 or index == len(rows):
                print(f"[label_gate_native] {index}/{len(rows)} | cat {counts['cat_present']} "
                      f"dog-only {counts['other_animal_only']} absent {counts['absent']}", flush=True)

    print(f"[label_gate_native] 完成 {len(rows)} 帧 → {args.out}；三态分布 {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
