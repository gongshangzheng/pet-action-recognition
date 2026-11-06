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
    parser.add_argument("--video-root", type=Path, required=True,
                        help="root the clip 'video' paths are relative to; used to clamp frame ranges")
    parser.add_argument("--clip-files", type=Path, default=None,
                        help="when set, read rendered clip mp4 files under this root and use 1..60 frames")
    return parser.parse_args()


def probe_frames(path: Path) -> int:
    import cv2

    capture = cv2.VideoCapture(str(path))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    return frames


def main() -> int:
    args = parse_args()
    lengths: dict[str, int] = {}
    dropped = 0
    index = {label: i for i, label in enumerate(CLASSES)}
    counts: dict[str, dict[str, int]] = {}
    args.out.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        rows: list[dict[str, Any]] = []
        candidates = [
            args.clips.parent / f"{split}.jsonl",
            args.clips.parent / "index" / f"{split}.jsonl",
        ]
        source = next((path for path in candidates if path.is_file()), candidates[0])
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise RuntimeError(f"unreadable split file: {source}") from error
        for line in lines:
            if not line.strip():
                continue
            clip = json.loads(line)
            label = clip["label"]
            if args.clip_files is not None:
                stem = Path(clip["video"]).stem
                name = f"{stem}__{clip['start']}-{clip['end']}__t{clip.get('track_id', 0)}.mp4"
                relative = Path(clip["split"]) / name
                if not (args.clip_files / relative).is_file():
                    dropped += 1
                    continue
                rows.append(
                    {
                        "video": str(relative),
                        "label": index[label],
                        "start_frame": 1,
                        "end_frame": 60,
                        "task_id": len(rows),
                        "sample_id": clip["sample_id"],
                        "species": clip.get("species"),
                    }
                )
                continue
            if label not in index:
                raise ValueError(f"unexpected label {label!r} in {source}")
            video = clip["video"]
            if video not in lengths:
                lengths[video] = probe_frames(args.video_root / video)
            frames = lengths[video]
            start_frame = max(1, int(clip["start"]))
            end_frame = min(int(clip["end"]), frames)
            if frames <= 0 or end_frame - start_frame + 1 < 8:
                dropped += 1
                continue
            rows.append(
                {
                    "video": video,
                    "label": index[label],
                    "start_frame": start_frame,
                    "end_frame": end_frame,
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
    print(json.dumps({"classes": CLASSES, "counts": counts, "dropped": dropped,
                      "videos_probed": len(lengths)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
