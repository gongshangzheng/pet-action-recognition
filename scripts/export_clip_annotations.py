#!/usr/bin/env python3
"""Convert clip manifests into annotation files the training loader accepts.

The clip manifest stores a string label and plain start/end; IntervalVideoDataset
expects an integer label plus start_frame/end_frame/task_id. This exporter maps
labels to the frozen class order and writes one file per split.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CLASSES = [
    "activity", "prolonged_stationary", "eating", "drinking", "toileting",
    "grooming", "scratching", "gnawing", "fall", "seizure",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = {label: i for i, label in enumerate(CLASSES)}
    counts: dict[str, dict[str, int]] = {}
    args.out.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        rows: list[dict[str, Any]] = []
        source = args.clips.parent / "index" / f"{split}.jsonl"
        if not source.is_file():
            raise FileNotFoundError(source)
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise RuntimeError(f"unreadable split file: {source}") from error
        for line in lines:
            if not line.strip():
                continue
            clip = json.loads(line)
            label = clip["label"]
            if label not in index:
                raise ValueError(f"unexpected label {label!r} in {source}")
            rows.append(
                {
                    "video": clip["video"],
                    "label": index[label],
                    "start_frame": int(clip["start"]),
                    "end_frame": int(clip["end"]),
                    "task_id": len(rows),
                    "sample_id": clip["sample_id"],
                    "species": clip.get("species"),
                }
            )
        target = args.out / f"{split}.jsonl"
        with target.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[split] = dict(
            sorted(
                {name: sum(1 for r in rows if r["label"] == i) for i, name in enumerate(CLASSES)}.items()
            )
        )
    (args.out / "classes.json").write_text(
        json.dumps(CLASSES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"classes": CLASSES, "counts": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
