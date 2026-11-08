#!/usr/bin/env python3
"""Merge every video source into one manifest: split, intervals, and pipeline status.

The pipeline currently learns its video set from three places: the source index
splits, a detection list and a manual missing list. This script writes one row
per annotated video with the status of each stage so later steps read a single
source.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True,
                        help="cat_raw intervals.csv: 权威的‘带标注视频’来源")
    parser.add_argument("--split-manifest", type=Path, required=True,
                        help="cat_action_v1 split_manifest.json: day → split 映射")
    parser.add_argument("--index-root", type=Path, default=None,
                        help="cat_action_v1 root, used only to mark in_index")
    parser.add_argument("--detections", type=Path, required=True)
    parser.add_argument("--clips", type=Path, default=None, help="rendered clip root, split subdirectories")
    parser.add_argument("--tracks", type=Path, default=None, help="track output directory")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"unreadable index split: {path}") from error
    for line in lines:
        if line.strip():
            rows.append(json.loads(line))
    return rows


def event_day(video: str) -> str | None:
    import re

    match = re.search(r"event_(\d{8})_", video)
    return match.group(1) if match else None


def main() -> int:
    args = parse_args()
    split_manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    day_split: dict[str, str] = {}
    for split, days in split_manifest["split_days"].items():
        for day in days:
            day_split[str(day)] = split

    import csv

    records: dict[str, dict[str, Any]] = {}
    with args.intervals.open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            video = row["video"]
            day = event_day(video)
            entry = records.setdefault(
                video,
                {
                    "video": video,
                    "split": day_split.get(day, "unassigned") if day else "unassigned",
                    "intervals": 0,
                    "splits": set(),
                },
            )
            entry["intervals"] += 1
            entry["splits"].add(entry["split"])

    indexed: set[str] = set()
    if args.index_root and args.index_root.is_dir():
        for split in ("train", "val", "test"):
            for row in read_jsonl(args.index_root / f"{split}.jsonl"):
                indexed.add(row["video"])

    detections = {path.stem for path in args.detections.glob("*.json")}
    clips: set[str] = set()
    if args.clips and args.clips.is_dir():
        for path in args.clips.glob("*/*.mp4"):
            clips.add(path.name.split("__")[0])
    tracks = set()
    if args.tracks and args.tracks.is_dir():
        tracks = {path.name.replace(".track.json", "") for path in args.tracks.glob("*.track.json")}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    status = Counter()
    with args.out.open("w", encoding="utf-8") as stream:
        for video in sorted(records):
            entry = records[video]
            stem = Path(video).stem
            entry["splits"] = sorted(entry["splits"])
            entry["detected"] = stem in detections
            entry["rendered"] = stem in clips
            entry["tracked"] = stem in tracks
            entry["in_index"] = video in indexed
            entry["complete"] = entry["detected"] and entry["rendered"] and entry["tracked"]
            status["videos"] += 1
            status["in_index"] += entry["in_index"]
            status["detected"] += entry["detected"]
            status["rendered"] += entry["rendered"]
            status["tracked"] += entry["tracked"]
            status["complete"] += entry["complete"]
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(dict(status), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
