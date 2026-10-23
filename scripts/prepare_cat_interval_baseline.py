#!/usr/bin/env python3
"""Create a balanced, day-disjoint cat interval training index without copying videos."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "datasets/cat_raw/annotations/intervals.csv"
VIDEOS = ROOT / "datasets/cat_raw"
OUTPUT = ROOT / "datasets/cat_interval_baseline"
AUDIT = ROOT / "results/training/cat_interval_baseline/data_audit.json"
CLASSES = ["common/activity", "common/eating", "common/prolonged_stationary",
           "common/drinking", "common/grooming", "abnormal/scratching"]
QUOTAS = {"train": 40, "val": 12, "test": 12}
SEED = 0
MIN_FRAMES = 60


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def day_of(video: str) -> str:
    match = re.search(r"event_(20[0-9]{6})_", video)
    return match.group(1) if match else "video:" + video


def stable_key(row: dict) -> str:
    return hashlib.sha256((str(SEED) + "|" + row["sample_id"]).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    global SOURCE, VIDEOS, OUTPUT, AUDIT
    root = args.root.resolve()
    SOURCE = root / "datasets/cat_raw/annotations/intervals.csv"
    VIDEOS = root / "datasets/cat_raw"
    OUTPUT = root / "datasets/cat_interval_baseline"
    AUDIT = root / "results/training/cat_interval_baseline/data_audit.json"

    from decord import VideoReader

    with SOURCE.open(encoding="utf-8", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in source_rows:
        by_video[row["video"]].append(row)
    counts = Counter()
    candidates = []
    for video, rows in by_video.items():
        for row in rows:
            label = row["label"]
            if label not in CLASSES:
                counts["other_class"] += 1
                continue
            start, end = int(row["start_frame"]), int(row["end_frame"])
            if end - start + 1 < MIN_FRAMES:
                counts["too_short"] += 1
                continue
            if any(other is not row and
                   max(start, int(other["start_frame"])) <= min(end, int(other["end_frame"]))
                   for other in rows):
                counts["overlapping"] += 1
                continue
            sample_id = hashlib.sha256((video + "|" + str(row["task_id"]) + "|"
                                        + str(start) + "|" + str(end) + "|" + label).encode()).hexdigest()[:20]
            candidates.append({"video": video, "task_id": int(row["task_id"]),
                               "start_frame": start, "end_frame": end,
                               "label": CLASSES.index(label), "label_name": label,
                               "day": day_of(video), "sample_id": sample_id})

    days = sorted({row["day"] for row in candidates})
    random.Random(SEED).shuffle(days)
    fifth = len(days) // 5
    split_days = {"val": set(days[:fifth]), "test": set(days[fifth:2 * fifth]),
                  "train": set(days[2 * fifth:])}
    frame_counts: dict[str, int | None] = {}
    invalid = Counter()
    selected: dict[str, list[dict]] = {}
    for split, quota in QUOTAS.items():
        chosen = []
        for label_index in range(len(CLASSES)):
            pool = sorted((row for row in candidates if row["day"] in split_days[split]
                           and row["label"] == label_index), key=stable_key)
            per_class = []
            for row in pool:
                video = row["video"]
                if video not in frame_counts:
                    try:
                        frame_counts[video] = len(VideoReader(str(VIDEOS / video), num_threads=1))
                    except Exception:
                        frame_counts[video] = None
                total = frame_counts[video]
                if total is None or row["end_frame"] > total:
                    invalid["unreadable_or_out_of_range"] += 1
                    continue
                per_class.append(row)
                if len(per_class) == quota:
                    break
            if len(per_class) != quota:
                raise RuntimeError(f"{split} {CLASSES[label_index]} has {len(per_class)}/{quota} valid samples")
            chosen.extend(per_class)
        selected[split] = sorted(chosen, key=stable_key)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for split, rows in selected.items():
        path = OUTPUT / f"{split}.jsonl"
        data = "".join(json.dumps({key: row[key] for key in
                                    ("video", "task_id", "start_frame", "end_frame", "label", "sample_id")},
                                   ensure_ascii=False) + "\n" for row in rows)
        if path.exists() and path.read_text(encoding="utf-8") != data:
            raise RuntimeError(f"Existing index differs: {path}")
        path.write_text(data, encoding="utf-8")
        outputs[split] = {"path": str(path), "rows": len(rows), "sha256": sha(path),
                          "classes": dict(Counter(row["label_name"] for row in rows))}
    classes_file = OUTPUT / "classes.json"
    classes_file.write_text(json.dumps(CLASSES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"source": str(SOURCE), "source_sha256": sha(SOURCE),
              "source_intervals": len(source_rows), "candidate_intervals": len(candidates),
              "filter_counts": dict(counts), "invalid_counts": dict(invalid),
              "frame_numbering": "1-based inclusive", "minimum_frames": MIN_FRAMES,
              "split_group": "event calendar day", "seed": SEED, "classes": CLASSES,
              "quotas_per_class": QUOTAS, "split_days": {k: sorted(v) for k, v in split_days.items()},
              "outputs": outputs, "selected_video_count": len({row["video"] for rows in selected.values() for row in rows})}
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outputs": outputs, "selected_video_count": report["selected_video_count"],
                      "invalid_counts": report["invalid_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
