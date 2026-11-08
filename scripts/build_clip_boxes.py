#!/usr/bin/env python3
"""Attach a per-frame box sequence to every clip using its track.

For each clip: pick the track that covers the most anchors inside the clip
window (single-target videos have exactly one), interpolate its anchor boxes to
every frame, hold the edge values where detections are missing, and smooth the
sequence with a 5-frame moving average. Output is a new clip manifest version so
the previous one stays comparable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SMOOTH_WINDOW = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--clip-frames", type=int, default=60)
    return parser.parse_args()


def load_tracks(directory: Path) -> dict[str, dict[str, Any]]:
    tracks = {}
    for path in directory.glob("*.track.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"unreadable track file: {path}") from error
        tracks[path.stem.replace(".track", "")] = payload
    return tracks


def interpolate(points: list[dict[str, Any]], frames: list[int]) -> list[list[float] | None]:
    """Linear interpolation over anchor boxes, holding the edges."""
    if not points:
        return [None] * len(frames)
    anchors = sorted(points, key=lambda item: item["frame"])
    boxes: list[list[float] | None] = []
    cursor = 0
    for frame in frames:
        while cursor + 1 < len(anchors) and anchors[cursor + 1]["frame"] <= frame:
            cursor += 1
        current = anchors[cursor]
        nxt = anchors[cursor + 1] if cursor + 1 < len(anchors) else None
        if nxt is None or frame <= current["frame"]:
            boxes.append(list(current["box"]))
            continue
        span = nxt["frame"] - current["frame"]
        ratio = (frame - current["frame"]) / span if span else 0.0
        boxes.append(
            [
                current["box"][i] + (nxt["box"][i] - current["box"][i]) * ratio
                for i in range(4)
            ]
        )
    return boxes


def smooth(boxes: list[list[float] | None]) -> list[list[float] | None]:
    radius = SMOOTH_WINDOW // 2
    out: list[list[float] | None] = []
    for index, box in enumerate(boxes):
        if box is None:
            out.append(None)
            continue
        window: list[list[float]] = []
        for i in range(max(0, index - radius), min(len(boxes), index + radius + 1)):
            neighbour = boxes[i]
            if neighbour is not None:
                window.append(neighbour)
        out.append([sum(w[i] for w in window) / len(window) for i in range(4)])
    return out


def main() -> int:
    args = parse_args()
    tracks = load_tracks(args.tracks)
    args.out.mkdir(parents=True, exist_ok=True)

    stats: defaultdict[str, int] = defaultdict(int)
    rows: list[dict[str, Any]] = []
    for line in args.clips.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            clip = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"malformed clip row: {line[:80]}") from error
        stem = clip["video"].split("/")[-1].replace(".mp4", "")
        payload = tracks.get(stem)
        if payload is None:
            stats["no_track_file"] += 1
            continue
        start, end = int(clip["start"]), int(clip["end"])
        frames = list(range(start, end + 1))
        best = None
        best_count = 0
        for track in payload["tracks"]:
            inside = [p for p in track["points"] if start <= p["frame"] <= end]
            if len(inside) > best_count:
                best, best_count = track, len(inside)
        if best is None or best_count == 0:
            stats["no_track_points"] += 1
            continue
        boxes = smooth(interpolate(best["points"], frames))
        if not any(boxes):
            stats["no_boxes"] += 1
            continue
        stats["clips_with_boxes"] += 1
        rows.append(
            {
                **clip,
                "track_id": best["track_id"],
                "track_species": best["species"],
                "boxes": [[round(v, 2) for v in b] if b else None for b in boxes],
                "box_frames": [start, end],
            }
        )

    with (args.out / "clips_v9.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    for split in ("train", "val", "test"):
        split_rows = sorted(
            (r for r in rows if r["split"] == split), key=lambda r: (r["video"], r["start"])
        )
        target = args.out / f"{split}.jsonl"
        with target.open("w", encoding="utf-8") as stream:
            for row in split_rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"clips_with_boxes": len(rows), "stats": dict(stats)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
