#!/usr/bin/env python3
"""Sample multi-pet intervals and draw their detection boxes for human review.

The multi-pet rule counts detections, and GroundingDINO also scores plush toys,
ornaments and posters as cats. This script picks a reproducible sample of the
intervals currently marked multi-pet, draws every box of the busiest anchor on
the frame, and writes an items.json describing what to check.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cv2

LABELS = {
    "common/activity", "common/eating", "common/drinking", "common/prolonged_stationary",
    "common/grooming", "common/toileting", "abnormal/scratching", "abnormal/gnawing",
    "abnormal/fall", "abnormal/seizure",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--detection-dir", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--coverage", type=float, default=0.5)
    parser.add_argument("--run", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def load_caches(directory: Path) -> dict[str, dict[str, Any]]:
    caches = {}
    for path in directory.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"unreadable detection cache: {path}") from error
        if payload.get("status") == "complete":
            caches[payload["video"].split("/")[-1]] = payload
    return caches


def multi_pet_intervals(rows, caches, coverage: float, run: int):
    found = []
    for row in rows:
        if row["label"] not in LABELS:
            continue
        cache = caches.get(row["video"].split("/")[-1])
        if cache is None:
            continue
        start, end = int(row["start_frame"]), int(row["end_frame"])
        anchors = {
            int(key): state for key, state in cache["anchors"].items() if start <= int(key) <= end
        }
        if not anchors:
            continue
        flags = [
            ((state.get("cat_count") or 0) + (state.get("dog_count") or 0)) >= 2
            for _, state in sorted(anchors.items())
        ]
        if sum(flags) / len(flags) < coverage:
            continue
        best = current = 0
        for flag in flags:
            current = current + 1 if flag else 0
            best = max(best, current)
        if best < run:
            continue
        busiest = max(
            anchors.items(),
            key=lambda kv: (kv[1].get("cat_count") or 0) + (kv[1].get("dog_count") or 0),
        )
        found.append({"row": row, "frame": busiest[0], "state": busiest[1]})
    return found


def draw(frame, state) -> Any:
    for cand in state.get("cat_candidates", []):
        x1, y1, x2, y2 = (int(v) for v in cand["box"])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 6)
        cv2.putText(frame, f"cat {cand['confidence']:.2f}", (x1 + 8, max(40, y1 + 46)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 4)
    for cand in state.get("dog_candidates", []):
        x1, y1, x2, y2 = (int(v) for v in cand["box"])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 6)
        cv2.putText(frame, f"dog {cand['confidence']:.2f}", (x1 + 8, max(40, y1 + 46)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 255), 4)
    return frame


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    caches = load_caches(args.detection_dir)
    rows = list(csv.DictReader(args.intervals.open(encoding="utf-8")))
    found = multi_pet_intervals(rows, caches, args.coverage, args.run)
    found.sort(key=lambda item: (item["row"]["video"], int(item["row"]["start_frame"])))
    chosen = rng.sample(found, min(args.count, len(found)))

    args.out.mkdir(parents=True, exist_ok=True)
    items = []
    for index, item in enumerate(chosen, start=1):
        row = item["row"]
        stem = row["video"].split("/")[-1]
        capture = cv2.VideoCapture(str(args.video_root / stem))
        capture.set(cv2.CAP_PROP_POS_FRAMES, item["frame"])
        ok, frame = capture.read()
        capture.release()
        if not ok:
            continue
        frame = draw(frame, item["state"])
        scale = 1440 / frame.shape[1]
        frame = cv2.resize(frame, (1440, int(frame.shape[0] * scale)))
        name = f"{index:02d}_{stem.replace('.mp4', '')}_{item['frame']}.jpg"
        cv2.imwrite(str(args.out / name), frame)
        items.append(
            {
                "file": name,
                "video": stem,
                "label": row["label"],
                "interval": [int(row["start_frame"]), int(row["end_frame"])],
                "anchor_frame": item["frame"],
                "pet_count": (item["state"].get("cat_count") or 0) + (item["state"].get("dog_count") or 0),
                "boxes": [
                    {"class": c["class"], "confidence": round(float(c["confidence"]), 3),
                     "box": [round(float(v)) for v in c["box"]]}
                    for c in item["state"].get("cat_candidates", []) + item["state"].get("dog_candidates", [])
                ],
            }
        )
    (args.out / "items.json").write_text(
        json.dumps({"seed": args.seed, "multi_pet_total": len(found), "items": items},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"multi_pet_total": len(found), "sampled": len(items),
                      "labels": dict(Counter(i["label"] for i in items))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
