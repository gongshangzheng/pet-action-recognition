#!/usr/bin/env python3
"""放大复核「只有狗」的帧：裁出 dog 框再跑一次 GroundingDINO，把被误判成狗的猫救回来。

背景：全量标注（tiles=3、阈值 0.15）里 `other_animal_only` 占 17.6%，但人工抽检 60 格时几乎见不到狗
→ 多数是「猫的 cat 分数没到阈值、dog 分数过线」。整图判不准时，把候选区域裁出来放大再判，
是提升局部判定的标准做法（等效于只对可疑区域提高分辨率）。

规则：
  - 输入：合并后的三态标签（`label == other_animal_only` 且有 `box_dog`）
  - 动作：以 dog 框为中心外扩 --expand 倍裁图 → GDINO（默认 800 短边）单次前向
  - 判定：裁图里 cat ≥ threshold → 改判 cat_present；否则保留 other_animal_only
  - 记录：原分数、裁图分数、是否改判（便于审计，不静默覆盖）

用法（GPU，2.6k 帧约 2–3 分钟）：
  python3 scripts/recheck_gate_dog_labels.py --labels results/gate/labels_native_all_t3.jsonl \
      --video-root ~/pet-final/datasets/cat_raw/videos --out results/gate/labels_native_final.jsonl \
      --threshold 0.15 --expand 2.0 --device cuda:0
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default="IDEA-Research/grounding-dino-tiny")
    parser.add_argument("--prompt", default="cat. dog.")
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--detect-threshold", type=float, default=0.05)
    parser.add_argument("--text-threshold", type=float, default=0.15)
    parser.add_argument("--expand", type=float, default=2.0, help="以 dog 框中心外扩倍数（2.0 = 边长翻倍）")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    import cv2
    import torch
    from PIL import Image
    from transformers import AutoProcessor, GroundingDinoForObjectDetection

    processor = AutoProcessor.from_pretrained(args.model_id)
    model = GroundingDinoForObjectDetection.from_pretrained(args.model_id).to(args.device).eval()

    rows = [json.loads(line) for line in args.labels.open(encoding="utf-8") if line.strip()]
    captures: dict[str, object] = {}
    counters = Counter()
    changed = 0
    pending = [row for row in rows if row.get("label") == "other_animal_only" and row.get("box_dog")]
    print(f"[recheck] 待复核 {len(pending)} 帧（dog-only 且有框），阈值 {args.threshold}，外扩 {args.expand}x")

    by_path: dict[str, dict] = {}
    for index, row in enumerate(pending, 1):
        video = str(args.video_root / row["video"])
        capture = captures.get(video)
        if capture is None:
            capture = cv2.VideoCapture(video)
            captures[video] = capture
        capture.set(cv2.CAP_PROP_POS_FRAMES, float(row["frame_idx"]))
        ok, frame_bgr = capture.read()
        if not ok:
            counters["decode_fail"] += 1
            by_path[row["path"]] = {"recheck": "decode_fail"}
            continue
        height, width = frame_bgr.shape[:2]
        x1, y1, x2, y2 = row["box_dog"]
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        half_w = max(32.0, (x2 - x1) * args.expand / 2)
        half_h = max(32.0, (y2 - y1) * args.expand / 2)
        crop = frame_bgr[max(0, int(center_y - half_h)):min(height, int(center_y + half_h)),
                         max(0, int(center_x - half_w)):min(width, int(center_x + half_w))]
        if crop.size == 0:
            counters["empty_crop"] += 1
            by_path[row["path"]] = {"recheck": "empty_crop"}
            continue
        image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        inputs = processor(images=image, text=args.prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            outputs = model(**inputs)
        result = processor.post_process_grounded_object_detection(
            outputs, inputs["input_ids"], box_threshold=args.detect_threshold,
            text_threshold=args.text_threshold, target_sizes=[image.size[::-1]])[0]
        texts = result.get("labels") or result.get("text_labels") or []
        best: dict[str, float] = {}
        for position, (box, score) in enumerate(zip(result["boxes"].tolist(), result["scores"].tolist())):
            label = str(texts[position]).strip().rstrip(".").lower() if position < len(texts) else "cat"
            best[label] = max(best.get(label, 0.0), float(score))
        recheck_cat, recheck_dog = best.get("cat", 0.0), best.get("dog", 0.0)
        verdict = "cat_present" if recheck_cat >= args.threshold else "other_animal_only"
        if verdict != row["label"]:
            changed += 1
        counters[verdict] += 1
        by_path[row["path"]] = {"recheck": verdict, "recheck_cat": round(recheck_cat, 4),
                                "recheck_dog": round(recheck_dog, 4)}
        if index % 200 == 0 or index == len(pending):
            print(f"[recheck] {index}/{len(pending)} | 改判 cat {changed}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    final = Counter()
    with args.out.open("w", encoding="utf-8") as stream:
        for row in rows:
            patch = by_path.get(row["path"])
            if patch:
                row.update(patch)
                if patch.get("recheck") in ("cat_present", "other_animal_only"):
                    row["label"] = patch["recheck"]
                    row["label_source"] = "recheck_zoom"
            row.setdefault("label_source", "native_gdino_t3")
            final[row["label"]] += 1
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[recheck] 完成：复核 {len(pending)} 帧，改判 {changed} 帧（{changed / max(1, len(pending)):.1%}）")
    print(f"[recheck] 最终三态：{dict(final)} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
