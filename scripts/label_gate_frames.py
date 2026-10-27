#!/usr/bin/env python3
"""门控帧级标签：教师标注（YOLO COCO-cat / GroundingDINO）→ 合并 → 冲突队列。

与 `prepare_gate_frames.py` 配套：那个脚本只产帧与元数据，这个脚本给每帧产「有猫」分数。

教师设计（openspec/changes/presence-gate-model design D10.2）：
- `--teacher yolo`：Ultralytics YOLO11n 的 COCO `cat` 类（无需训练），score = 最高 cat 框置信度。
- `--teacher gdino`：GroundingDINO-tiny，prompt `cat. dog.`，主分数 = 最高 cat 框置信度；dog 单列记录
  （实测语料里混有狗 → 猫门控必须能区分「有猫」与「只有狗」）。
- 两者都能跑完后，用 `merge` 子命令合并：一致 → 采用；冲突（一高一低）→ 进人工队列。

产物（JSONL，一帧一行）：
  {"path": "...", "teacher": "yolo", "score": 0.83, "box": [x1,y1,x2,y2] | null, "n_boxes": 1}

用法：
  # 教师 A（快，推荐先跑）
  python scripts/label_gate_frames.py yolo --manifest results/gate/dataset_v1/manifest.csv \
      --weights ~/pet-final/weights/yolo11n.pt --out results/gate/labels_yolo.jsonl --batch 64

  # 教师 B（慢，GPU；同时查 cat 与 dog）
  python scripts/label_gate_frames.py gdino --manifest ... --out results/gate/labels_gdino.jsonl

  # 合并 + 冲突队列
  python scripts/label_gate_frames.py merge --manifest ... \
      --yolo results/gate/labels_yolo.jsonl --gdino results/gate/labels_gdino.jsonl \
      --out results/gate/labels_merged.jsonl --queue results/gate/manual_queue.csv \
      --agree-threshold 0.5 --conflict-margin 0.25
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def read_manifest(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_yolo(args: argparse.Namespace) -> int:
    from ultralytics import YOLO

    rows = read_manifest(args.manifest)
    root = args.image_root or args.manifest.parent
    model = YOLO(str(args.weights))
    cat_class = int(args.cat_class)
    out: list[dict] = []
    batch: list[dict] = []

    def flush(chunk: list[dict]) -> None:
        paths = [str(root / row["path"]) for row in chunk]
        results = model.predict(paths, imgsz=args.imgsz, conf=args.conf, verbose=False, device=args.device)
        for row, result in zip(chunk, results):
            best_score, best_box = 0.0, None
            boxes = result.boxes
            if boxes is not None and len(boxes):
                for box, score, cls in zip(boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()):
                    if int(cls) == cat_class and float(score) > best_score:
                        best_score, best_box = float(score), [round(v, 1) for v in box]
            out.append({"path": row["path"], "teacher": "yolo", "score": round(best_score, 4), "box": best_box})
        print(f"[label_gate] yolo {len(out)}/{len(rows)}", flush=True)

    for row in rows:
        batch.append(row)
        if len(batch) >= args.batch:
            flush(batch)
            batch = []
    if batch:
        flush(batch)
    write_jsonl(args.out, out)
    print(f"[label_gate] yolo 完成 {len(out)} 帧 → {args.out}")
    return 0


def cmd_gdino(args: argparse.Namespace) -> int:
    import torch
    from PIL import Image
    from transformers import AutoProcessor, GroundingDinoForObjectDetection

    rows = read_manifest(args.manifest)
    root = args.image_root or args.manifest.parent
    device = args.device if args.device != "cpu" else "cpu"
    processor = AutoProcessor.from_pretrained(args.model_id)
    model = GroundingDinoForObjectDetection.from_pretrained(args.model_id).to(device).eval()
    out: list[dict] = []

    for index, row in enumerate(rows, 1):
        image = Image.open(root / row["path"]).convert("RGB")
        inputs = processor(images=image, text=args.prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        result = processor.post_process_grounded_object_detection(
            outputs, inputs["input_ids"], threshold=args.threshold,
            text_threshold=args.text_threshold, target_sizes=[image.size[::-1]])[0]
        boxes = result["boxes"].tolist()
        scores = result["scores"].tolist()
        # transformers 4.49 的返回键是 labels；缺省时退化为「全部当 cat」，避免静默丢标签
        texts = result.get("labels") or result.get("text_labels") or []
        per_class: dict[str, float] = {}
        per_class_box: dict[str, list[float]] = {}
        for position, (box, score) in enumerate(zip(boxes, scores)):
            label = str(texts[position]) if position < len(texts) else "cat"
            label = label.strip().rstrip(".").lower()
            if float(score) > per_class.get(label, 0.0):
                per_class[label] = float(score)
                per_class_box[label] = [round(v, 1) for v in box]
        out.append({
            "path": row["path"], "teacher": "gdino",
            "score": round(per_class.get("cat", 0.0), 4),          # 主分数 = cat
            "box": per_class_box.get("cat"),
            "score_dog": round(per_class.get("dog", 0.0), 4),       # 语料里确实混有狗，单列记录
            "box_dog": per_class_box.get("dog"),
            "per_class": {k: round(v, 4) for k, v in sorted(per_class.items())},
        })
        if index % 50 == 0 or index == len(rows):
            print(f"[label_gate] gdino {index}/{len(rows)}", flush=True)

    write_jsonl(args.out, out)
    print(f"[label_gate] gdino 完成 {len(out)} 帧 → {args.out}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    def load(path: Path) -> dict[str, dict]:
        return {json.loads(line)["path"]: json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

    yolo = load(args.yolo)
    gdino = load(args.gdino) if args.gdino and Path(args.gdino).is_file() else {}
    manifest = {row["path"]: row for row in read_manifest(args.manifest)}

    merged, queue = [], []
    for path, row in manifest.items():
        sy = yolo.get(path, {}).get("score")
        sg = gdino.get(path, {}).get("score") if gdino else None
        scores = [s for s in (sy, sg) if s is not None]
        if not scores:
            queue.append({**row, "reason": "no_teacher", "score_yolo": "", "score_gdino": ""})
            continue
        label = "present" if max(scores) >= args.agree_threshold else "absent"
        conflict = False
        if sy is not None and sg is not None:
            # 一个过阈值、一个远低于阈值 → 冲突
            conflict = (max(sy, sg) >= args.agree_threshold) and (min(sy, sg) < args.agree_threshold - args.conflict_margin)
        merged.append({
            "path": path, "label": label, "score_yolo": sy, "score_gdino": sg,
            "agreement": "conflict" if conflict else ("dual" if sg is not None else "single"),
            "domain": row["domain"], "split": row["split"], "date": row["date"], "group": row["group"],
        })
        if conflict:
            queue.append({**{k: row[k] for k in ("path", "video", "date", "domain", "split", "group")},
                          "reason": "teacher_conflict", "score_yolo": sy, "score_gdino": sg})

    write_jsonl(args.out, merged)
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    with args.queue.open("w", encoding="utf-8", newline="") as stream:
        fields = ["path", "video", "date", "domain", "split", "group", "reason", "score_yolo", "score_gdino"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(queue)
    present = sum(1 for r in merged if r["label"] == "present")
    print(f"[label_gate] 合并 {len(merged)} 帧：present {present} / absent {len(merged) - present}；人工队列 {len(queue)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("yolo", "gdino"):
        p = sub.add_parser(name)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--image-root", type=Path, default=None,
                       help="图片根目录（默认 = manifest 所在目录）；帧清单可放在别处")
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--batch", type=int, default=64 if name == "yolo" else 8)
        p.add_argument("--device", default="cuda:0")
    y = sub.choices["yolo"]
    y.add_argument("--weights", type=Path, required=True)
    y.add_argument("--imgsz", type=int, default=640)
    y.add_argument("--conf", type=float, default=0.05)
    y.add_argument("--cat-class", type=int, default=15, help="COCO 的 cat 类索引（默认 15）")
    g = sub.choices["gdino"]
    g.add_argument("--model-id", default="IDEA-Research/grounding-dino-tiny")
    g.add_argument("--prompt", default="cat. dog.", help="多类别提示；主分数取 cat，dog 单列记录")
    g.add_argument("--threshold", type=float, default=0.05)
    g.add_argument("--text-threshold", type=float, default=0.15)

    m = sub.add_parser("merge")
    m.add_argument("--manifest", type=Path, required=True)
    m.add_argument("--yolo", type=Path, required=True)
    m.add_argument("--gdino", type=Path, default=None)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--queue", type=Path, required=True)
    m.add_argument("--agree-threshold", type=float, default=0.5)
    m.add_argument("--conflict-margin", type=float, default=0.25)

    args = parser.parse_args()
    return {"yolo": cmd_yolo, "gdino": cmd_gdino, "merge": cmd_merge}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
