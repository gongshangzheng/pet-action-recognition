#!/usr/bin/env python3
"""Build a browser-reviewable raw/GroundingDINO/motion clip set.

The script intentionally exports short, frame-accurate clips for the annotated
interval instead of copying full source videos. All three arms share the same
interval and output geometry, so the review UI can synchronize playback.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any


ARMS = ("raw", "gdino", "gdino_motion")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def probe_fps(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    stream = (payload.get("streams") or [{}])[0]
    rate = stream.get("avg_frame_rate")
    if not rate or rate in {"0/0", "0"}:
        raise ValueError(f"Cannot determine FPS: {path}")
    fps = float(Fraction(rate))
    if fps <= 0:
        raise ValueError(f"Invalid FPS {fps}: {path}")
    return fps


def export_clip(
    source: Path,
    output: Path,
    start_frame: int,
    end_frame: int,
    fps: float,
    crf: int,
) -> None:
    if start_frame < 1 or end_frame < start_frame:
        raise ValueError(f"Invalid 1-based interval {start_frame}-{end_frame}")
    filter_graph = (
        f"trim=start_frame={start_frame - 1}:end_frame={end_frame},"
        "setpts=PTS-STARTPTS,"
        "scale=512:512:force_original_aspect_ratio=decrease,"
        "pad=512:512:(ow-iw)/2:(oh-ih)/2:color=114"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".mp4.writing.mp4")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        filter_graph,
        "-an",
        "-r",
        f"{fps:.12f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-threads",
        "2",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    subprocess.run(command, check=True)
    os.replace(temporary, output)


def generated_path(asset_root: Path, arm: str, video: str) -> Path:
    if arm not in {"gdino", "gdino_motion"}:
        raise ValueError(f"Unsupported generated arm: {arm}")
    return asset_root / "videos" / arm / f"{Path(video).stem}.mp4"


def availability_by_sample(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["sample_id"]): row for row in payload.get("rows", [])}


def build_review_set(args: argparse.Namespace) -> dict[str, Any]:
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    rows = selection.get("rows") or []
    availability = availability_by_sample(args.availability)
    items: list[dict[str, Any]] = []
    args.output.mkdir(parents=True, exist_ok=True)

    for index, row in enumerate(rows, 1):
        review_id = f"Q{index:03d}"
        source = args.source_root / row["video"]
        inputs = {
            "raw": source,
            "gdino": generated_path(args.asset_root, "gdino", row["video"]),
            "gdino_motion": generated_path(
                args.asset_root, "gdino_motion", row["video"]
            ),
        }
        missing = [str(path) for path in inputs.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                f"{review_id} missing source/generated media: {missing}"
            )
        fps = probe_fps(source)
        relative_files: dict[str, str] = {}
        for arm in ARMS:
            relative = Path("media") / review_id / f"{arm}.mp4"
            destination = args.output / relative
            if args.force or not destination.is_file():
                export_clip(
                    inputs[arm],
                    destination,
                    int(row["start_frame"]),
                    int(row["end_frame"]),
                    fps,
                    args.crf,
                )
            relative_files[arm] = relative.as_posix()
        availability_row = availability.get(str(row["sample_id"]), {})
        items.append(
            {
                "path": review_id,
                "file": relative_files["raw"],
                "files": relative_files,
                "review_id": review_id,
                "sample_id": row["sample_id"],
                "video": row["video"],
                "class_name": row["class_name"],
                "label": row["label"],
                "start_frame": int(row["start_frame"]),
                "end_frame": int(row["end_frame"]),
                "frame_count": int(row["frame_count"]),
                "fps": fps,
                "event_hour": row.get("event_hour"),
                "selection_reasons": row.get("selection_reasons") or [],
                "strict_available": bool(availability_row.get("available", False)),
                "unavailable_reason": availability_row.get("unavailable_reason"),
                "invalid_frames": int(availability_row.get("invalid_frames", 0)),
            }
        )
        print(f"[review] {review_id}: {row['class_name']} frames={row['frame_count']}", flush=True)

    payload = {
        "schema": "gate-video-review-set-v1",
        "created_utc": utc_now(),
        "title": "GroundingDINO 裁剪人工审阅：20 段",
        "mode": "crop_comparison",
        "hide_teacher": True,
        "count": len(items),
        "selection": str(args.selection),
        "selection_sha256": args.selection_sha256,
        "arms": list(ARMS),
        "items": items,
    }
    atomic_json(args.output / "items.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--selection-sha256", default="")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--availability", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--crf", type=int, default=22)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.crf <= 51:
        parser.error("--crf must be between 0 and 51")
    return args


def main() -> None:
    payload = build_review_set(parse_args())
    print(json.dumps({"count": payload["count"], "mode": payload["mode"]}))


if __name__ == "__main__":
    main()
