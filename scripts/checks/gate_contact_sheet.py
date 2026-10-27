#!/usr/bin/env python3
"""门控人工核验接触表：把帧拼成带标注的网格图，供人眼判 present / absent / uncertain。

每张图 N 列 × M 行，每格左上角标 `序号 | 分数 | 域 | split`，可选叠加检测框。
产物命名 `<prefix>_sheet{k}.jpg`，配套 CSV 记录每格对应的帧路径（人工判定结果回填该 CSV）。

用法：
  python scripts/checks/gate_contact_sheet.py \
      --manifest results/gate/dataset_v1/manifest.csv --labels results/gate/labels_yolo.jsonl \
      --image-root results/gate/dataset_v1 --out results/gate/review \
      --per-sheet 20 --cols 4 --sheets 3 --strategy stratify
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

TILE_SIZE = (480, 270)  # 每格像素（16:9）


def load_labels(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as stream:
        return {json.loads(line)["path"]: json.loads(line) for line in stream if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-sheet", type=int, default=20)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--sheets", type=int, default=3)
    parser.add_argument("--strategy", choices=["stratify", "low", "high", "night", "queue"], default="stratify")
    parser.add_argument("--queue", type=Path, default=None, help="strategy=queue 时的 CSV（含 path 列）")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--draw-box", action="store_true", help="叠加教师检测框")
    args = parser.parse_args()

    import cv2
    import numpy as np

    labels = load_labels(args.labels)
    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    def score(row: dict) -> float:
        return float(labels.get(row["path"], {}).get("score") or 0.0)

    if args.strategy == "queue" and args.queue:
        with args.queue.open(encoding="utf-8", newline="") as stream:
            queued = [row["path"] for row in csv.DictReader(stream)]
        keep = set(queued)
        pool = [row for row in rows if row["path"] in keep]
    elif args.strategy == "low":
        pool = [row for row in rows if score(row) < 0.05]
    elif args.strategy == "high":
        pool = [row for row in rows if score(row) >= 0.7]
    elif args.strategy == "night":
        pool = [row for row in rows if row["domain"] == "night"]
    else:  # stratify：high / mid / low / night 各 1/4
        buckets = {"high": [], "mid": [], "low": [], "night": []}
        for row in rows:
            if row["domain"] == "night":
                buckets["night"].append(row)
            elif score(row) >= 0.7:
                buckets["high"].append(row)
            elif 0.2 <= score(row) < 0.5:
                buckets["mid"].append(row)
            elif score(row) < 0.05:
                buckets["low"].append(row)
        pool = []
        for name, bucket in buckets.items():
            random.Random(args.seed).shuffle(bucket)
            pool.extend(bucket[: args.per_sheet * args.sheets // 4 + 2])

    random.Random(args.seed).shuffle(pool)
    args.out.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict] = []

    for sheet in range(args.sheets):
        chunk = pool[sheet * args.per_sheet:(sheet + 1) * args.per_sheet]
        if not chunk:
            break
        rows_per_sheet = (len(chunk) + args.cols - 1) // args.cols
        canvas = np.full((rows_per_sheet * TILE_SIZE[1], args.cols * TILE_SIZE[0], 3), 32, np.uint8)
        for position, row in enumerate(chunk):
            image = cv2.imread(str(args.image_root / row["path"]))
            if image is None:
                continue
            image = cv2.resize(image, TILE_SIZE, interpolation=cv2.INTER_AREA)
            entry = labels.get(row["path"], {})
            if args.draw_box and entry.get("box"):
                x1, y1, x2, y2 = entry["box"]
                scale_x = TILE_SIZE[0] / float(row["width"])
                scale_y = TILE_SIZE[1] / float(row["height"])
                cv2.rectangle(image, (int(x1 * scale_x), int(y1 * scale_y)),
                              (int(x2 * scale_x), int(y2 * scale_y)), (0, 255, 0), 2)
            text = f"#{sheet * args.per_sheet + position + 1} s={entry.get('score', 0):.2f} {row['domain']}/{row['split']}"
            cv2.putText(image, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(image, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            y = (position // args.cols) * TILE_SIZE[1]
            x = (position % args.cols) * TILE_SIZE[0]
            canvas[y:y + TILE_SIZE[1], x:x + TILE_SIZE[0]] = image
            index_rows.append({"sheet": sheet + 1, "cell": position + 1, "path": row["path"],
                               "video": row["video"], "domain": row["domain"], "split": row["split"],
                               "teacher_score": entry.get("score"), "human_label": ""})
        target = args.out / f"sheet{sheet + 1}.jpg"
        cv2.imwrite(str(target), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"[contact_sheet] {target} （{len(chunk)} 格）")

    with (args.out / "review_index.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sheet", "cell", "path", "video", "domain", "split",
                                                    "teacher_score", "human_label"])
        writer.writeheader()
        writer.writerows(index_rows)
    print(f"[contact_sheet] 索引 → {args.out / 'review_index.csv'}（人工填 human_label: present/absent/uncertain）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
