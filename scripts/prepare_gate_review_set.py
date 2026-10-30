#!/usr/bin/env python3
"""抽样构建「人工核验集」：按场景分层抽帧 + 写入 items.json（含教师判定与框）。

场景条件（每条 ≥ --per-scenario 帧，全部来自 dataset_v1 的帧与 native 教师标签）：

| 场景 | 判定条件 |
|---|---|
| `still` | 有宠物，且该帧所在视频段内连续 ≥5 s 探测框几乎不动（框中心位移 < 2% 画面宽） |
| `small` | 有宠物，且猫框短边 < 32 px（按原生分辨率换算） |
| `occluded` | 有宠物，但教师 cat 分数在灰带（0.15–0.30）——最难判的一档 |
| `out_of_frame` | 标签为 absent（教师未检出）——含出入画/空场 |
| `day` / `night` | 前四类之外的昼夜补充（保证两域都有量） |

产物（一个 review set 一个目录）：

  <out>/items.json        # 每帧：path/label(教师)/scores/boxes/scenario/domain/split
  <out>/frames/<path>     # 帧文件（软链或复制，默认复制，便于整体搬到本机）
  <out>/labels.csv        # 人工标注表（表头已建好，human_label 留空）

用法：
  python3 scripts/prepare_gate_review_set.py --manifest results/gate/dataset_v1/manifest.csv \
      --labels results/gate/labels_native_all_t3.jsonl --image-root results/gate/dataset_v1 \
      --out results/gate/review/set1 --per-scenario 40
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path


def box_center(box: list[float] | None) -> tuple[float, float] | None:
    if not box:
        return None
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-scenario", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--copy", action="store_true", default=True, help="复制帧（默认；--link 可改为软链）")
    parser.add_argument("--link", dest="copy", action="store_false")
    args = parser.parse_args()

    labels = {}
    with args.labels.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if "label" in row:
                    labels[row["path"]] = row

    with args.manifest.open(encoding="utf-8", newline="") as stream:
        manifest = list(csv.DictReader(stream))

    # 按视频聚合，判断 still（框中心在 ±5 s 窗口内位移很小）
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in manifest:
        by_video[row["video"]].append(row)
    for video in by_video:
        by_video[video].sort(key=lambda r: int(r["frame_idx"]))

    still_paths = set()
    for video, group in by_video.items():
        centers = []
        for row in group:
            entry = labels.get(row["path"], {})
            centers.append((box_center(entry.get("box_cat")), row["width"]))
        for index, (center, width) in enumerate(centers):
            if center is None:
                continue
            window = [c for c, _ in centers[max(0, index - 5):index + 1] if c is not None]
            if len(window) < 3:
                continue
            xs = [c[0] for c in window]
            ys = [c[1] for c in window]
            spread = max(max(xs) - min(xs), max(ys) - min(ys))
            if spread < 0.02 * int(width):
                still_paths.add(group[index]["path"])

    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in manifest:
        entry = labels.get(row["path"])
        if not entry:
            continue
        label = entry.get("label", "absent")
        cat = float(entry.get("score_cat") or 0.0)
        box = entry.get("box_cat")
        short_side = min(box[2] - box[0], box[3] - box[1]) if box else 0.0
        if row["path"] in still_paths:
            buckets["still"].append({**row, "entry": entry})
        if label != "absent" and 0 < short_side < 32:
            buckets["small"].append({**row, "entry": entry})
        if label != "absent" and 0.15 <= cat < 0.30:
            buckets["occluded"].append({**row, "entry": entry})
        if label == "absent":
            buckets["out_of_frame"].append({**row, "entry": entry})
        buckets[row["domain"]].append({**row, "entry": entry})

    rng = random.Random(args.seed)
    picked: list[dict] = []
    seen: set[str] = set()
    for scenario in ("still", "small", "occluded", "out_of_frame", "day", "night"):
        pool = [row for row in buckets.get(scenario, []) if row["path"] not in seen]
        rng.shuffle(pool)
        take = pool[: args.per_scenario]
        for row in take:
            row["scenario"] = scenario
            seen.add(row["path"])
        picked.extend(take)
        print(f"[review-set] {scenario:13s} 池 {len(buckets.get(scenario, [])):5d} → 取 {len(take)}")

    args.out.mkdir(parents=True, exist_ok=True)
    frames_dir = args.out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for row in picked:
        source = args.image_root / row["path"]
        target = args.out / row["path"]        # row["path"] 已形如 frames/<date>/<name>.jpg
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            if args.copy:
                shutil.copy2(source, target)
            else:
                target.symlink_to(source.resolve())
        entry = row["entry"]
        items.append({
            "path": row["path"],
            "file": row["path"],
            "video": row["video"],
            "date": row["date"],
            "group": row["group"],
            "domain": row["domain"],
            "split": row["split"],
            "scenario": row["scenario"],
            "teacher_label": entry.get("label"),
            "score_cat": entry.get("score_cat"),
            "score_dog": entry.get("score_dog"),
            "box_cat": entry.get("box_cat"),
            "box_dog": entry.get("box_dog"),
            "width": int(row["width"]),
            "height": int(row["height"]),
            "human_label": "",
        })

    (args.out / "items.json").write_text(json.dumps({"count": len(items), "items": items},
                                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.out / "labels.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "scenario", "domain", "split",
                                                    "teacher_label", "score_cat", "human_label", "note"])
        writer.writeheader()
        for item in items:
            writer.writerow({"path": item["path"], "scenario": item["scenario"], "domain": item["domain"],
                             "split": item["split"], "teacher_label": item["teacher_label"],
                             "score_cat": item["score_cat"], "human_label": "", "note": ""})
    print(f"[review-set] 完成 {len(items)} 帧 → {args.out}（items.json / frames/ / labels.csv）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
