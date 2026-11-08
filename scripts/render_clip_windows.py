#!/usr/bin/env python3
"""Render each clip to a 256x256 mp4 file using its per-frame boxes.

Offline rendering keeps the training input auditable (frame count, size, hash)
and removes any crop work from the training loop.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petlib.videowriter import H264VideoWriter  # noqa: E402

SIZE = 256
BACKGROUND = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True, help="clips_v9.jsonl with boxes")
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--fps", type=float, default=15.0)
    parser.add_argument("--crf", type=int, default=23)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def square_crop(frame: np.ndarray, box: list[float]) -> np.ndarray:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = box
    side = max(1, int(round(max(x2 - x1, y2 - y1))))
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    left, top = int(round(cx - side / 2)), int(round(cy - side / 2))
    canvas = np.full((side, side, frame.shape[2]), BACKGROUND, dtype=frame.dtype)
    sl, st = max(0, left), max(0, top)
    sr, sb = min(width, left + side), min(height, top + side)
    if sr <= sl or sb <= st:
        raise ValueError(f"box outside frame: {box}")
    canvas[st - top : sb - top, sl - left : sr - left] = frame[st:sb, sl:sr]
    return cv2.resize(canvas, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def render_one(job: dict[str, Any]) -> dict[str, Any]:
    source = Path(job["source"])
    target = Path(job["target"])
    boxes = job["boxes"]
    start = job["start"]
    target.parent.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        return {"ok": False, "target": str(target), "reason": "cannot_open"}
    capture.set(cv2.CAP_PROP_POS_FRAMES, start - 1)
    writer = H264VideoWriter(str(target), job["fps"], (SIZE, SIZE), crf=job["crf"], threads=1)
    written = 0
    try:
        for offset, box in enumerate(boxes):
            ok, frame = capture.read()
            if not ok:
                return {"ok": False, "target": str(target), "reason": f"decode_stop@{offset}"}
            writer.write(square_crop(frame, box) if box else cv2.resize(frame, (SIZE, SIZE)))
            written += 1
    finally:
        writer.release()
        capture.release()
    return {"ok": written == len(boxes), "target": str(target), "frames": written}


def main() -> int:
    args = parse_args()
    rows = []
    for line in args.clips.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"malformed clip row: {line[:80]}") from error
    if args.limit:
        rows = rows[: args.limit]

    jobs = []
    for row in rows:
        stem = Path(row["video"]).stem
        name = f"{stem}__{row['start']}-{row['end']}__t{row['track_id']}.mp4"
        jobs.append(
            {
                "source": str(args.video_root / row["video"]),
                "target": str(args.out / row["split"] / name),
                "boxes": row["boxes"],
                "start": int(row["start"]),
                "fps": args.fps,
                "crf": args.crf,
            }
        )
    args.out.mkdir(parents=True, exist_ok=True)
    failures = []
    done = 0
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for result in pool.imap_unordered(render_one, jobs, chunksize=8):
            done += 1
            if not result["ok"]:
                failures.append(result)
            if done % 200 == 0:
                print(f"[render] {done}/{len(jobs)} failures={len(failures)}", flush=True)
    print(json.dumps({"rendered": done, "failures": len(failures),
                      "samples": failures[:5]}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
