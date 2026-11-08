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
    parser.add_argument("--index-root", type=Path, required=True, help="cat_action_v1 root with train/val/test.jsonl")
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


def main() -> int:
    args = parse_args()
    records: dict[str, dict[str, Any]] = {}
    for split in ("train", "val", "test"):
        for row in read_jsonl(args.index_root / f"{split}.jsonl"):
            video = row["video"]
            entry = records.setdefault(
                video, {"video": video, "split": split, "intervals": 0, "splits": set()}
            )
            entry["intervals"] += 1
            entry["splits"].add(split)

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
            entry["complete"] = entry["detected"] and entry["rendered"] and entry["tracked"]
            status["videos"] += 1
            status["detected"] += entry["detected"]
            status["rendered"] += entry["rendered"]
            status["tracked"] += entry["tracked"]
            status["complete"] += entry["complete"]
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(dict(status), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
