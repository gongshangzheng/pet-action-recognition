#!/usr/bin/env python3
"""把一条标注区间的**完整时间跨度**渲染成可对照的素材。

片段级分析里常见一种误读：模型看的 4 秒「几乎不动」，于是被当成模型分不清，
但标注区间的其余部分其实有明确动作。这个脚本把区间整体拉出来，用于和片段并排对照：

- `<video>__<start>-<end>-interval-crop.mp4`：整个区间按轨迹逐帧框裁剪（与训练输入同一裁剪策略、同一 256×256）；
- `<video>__<start>-<end>-interval-full.mp4`：整个区间的原画（缩到 640 宽），保留场景上下文；
- `<video>__<start>-<end>-interval-strip.jpg`：区间内均匀 12 帧的裁剪拼图，静态浏览用。

框的来源与训练一致：取区间内命中最多的同一条轨迹，把锚点框线性插值到每一帧、端点保持，
再做 5 帧滑动平均（复用 `scripts/build_clip_boxes.py` 的同名函数）。

用法（在仓库根目录）：

    python3 scripts/render_interval_excerpt.py \
        --clips results/cat_clip_v9/index/clips_v9.jsonl \
        --tracks-dir results/cat_clip_v9/tracks \
        --video-root ~/pet-final/datasets/cat_raw \
        --sample-id "event_20260802_053844:1-235:activity" \
        --out results/class_error_analysis/full_interval

    # 只要某条轨迹 / 只换输出名
    python3 scripts/render_interval_excerpt.py ... --track-id 0 --name activity-001
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

SCRIPTS = Path(__file__).resolve().parent
_DEPS: dict[str, Any] = {}


def local_deps() -> dict[str, Any]:
    """延迟导入同目录脚本与仓库 lib：放模块级会与第三方 import 块混排，顺序检查过不去。"""
    if _DEPS:
        return _DEPS
    for path in (str(SCRIPTS), str(SCRIPTS.parent)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from build_clip_boxes import interpolate, smooth
    from lib.videowriter import H264VideoWriter
    from render_clip_windows import SIZE, square_crop

    _DEPS.update(
        SIZE=SIZE, square_crop=square_crop, interpolate=interpolate,
        smooth=smooth, H264VideoWriter=H264VideoWriter,
    )
    return _DEPS

STRIP_FRAMES = 12
STRIP_COLS = 4
FULL_WIDTH = 640


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clips", type=Path, required=True, help="带 boxes 的片段清单（clips_v9.jsonl）")
    parser.add_argument("--tracks-dir", type=Path, required=True, help="*.track.json 所在目录")
    parser.add_argument("--video-root", type=Path, required=True, help="清单里 video 字段的相对根（其下有 videos/）")
    parser.add_argument("--sample-id", required=True, help="形如 video:start-end:label")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", default="", help="输出文件名前缀，默认用 video 名 + 区间")
    parser.add_argument("--track-id", type=int, default=None, help="指定轨迹；默认用区间内命中最多的那条")
    parser.add_argument("--crf", type=int, default=22)
    return parser.parse_args()


def as_int(value: Any, what: str) -> int:
    """把清单/轨迹里的数字转成 int，坏值给一句能定位的错，而不是抛裸 ValueError。"""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"{what} 不是整数：{value!r}") from error


def as_float(value: Any, what: str, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def load_rows(clips: Path, sample_id: str) -> list[dict[str, Any]]:
    try:
        text = clips.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"读不到片段清单：{clips}（{error}）") from error
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"{clips}:{number} 不是合法 JSON（{error.msg}）") from error
        if row.get("sample_id") == sample_id:
            rows.append(row)
    if not rows:
        raise SystemExit(f"清单里没有 sample_id={sample_id}")
    return rows


def parse_interval(sample_id: str) -> tuple[str, int, int, str]:
    parts = sample_id.rsplit(":", 2)
    if len(parts) != 3 or "-" not in parts[1]:
        raise SystemExit(f"sample_id 形状应为 video:start-end:label，得到 {sample_id!r}")
    stem, span, label = parts
    start, end = span.split("-", 1)
    return stem, as_int(start, "区间起始帧"), as_int(end, "区间结束帧"), label


def pick_track(track_payload: dict[str, Any], start: int, end: int,
               track_id: int | None) -> dict[str, Any]:
    tracks = track_payload.get("tracks", [])
    if track_id is not None:
        for track in tracks:
            if as_int(track.get("track_id", -1), "轨迹 id") == track_id:
                return track
        raise SystemExit(f"轨迹文件里没有 track_id={track_id}")
    best, best_count = None, 0
    for track in tracks:
        inside = [p for p in track.get("points", []) if start <= p["frame"] <= end]
        if len(inside) > best_count:
            best, best_count = track, len(inside)
    if best is None:
        raise SystemExit("区间内没有任何轨迹点，无法裁剪")
    return best


def render(source: Path, out_dir: Path, prefix: str, start: int, end: int,
           boxes: list[list[float] | None], crf: int) -> dict[str, Any]:
    deps = local_deps()
    SIZE, square_crop = deps["SIZE"], deps["square_crop"]
    H264VideoWriter = deps["H264VideoWriter"]
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise SystemExit(f"打不开源视频：{source}")
    fps = as_float(capture.get(cv2.CAP_PROP_FPS), "源视频帧率", 15.0) or 15.0
    width = as_int(capture.get(cv2.CAP_PROP_FRAME_WIDTH), "源视频宽度")
    height = as_int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT), "源视频高度")
    capture.set(cv2.CAP_PROP_POS_FRAMES, start - 1)

    frames_total = end - start + 1
    out_dir.mkdir(parents=True, exist_ok=True)
    crop_path = out_dir / f"{prefix}-interval-crop.mp4"
    full_path = out_dir / f"{prefix}-interval-full.mp4"
    strip_path = out_dir / f"{prefix}-interval-strip.jpg"

    full_w = min(FULL_WIDTH, width)
    full_h = max(2, as_int(round(height * full_w / width / 2) * 2, "输出高度"))
    crop_writer = H264VideoWriter(str(crop_path), fps, (SIZE, SIZE), crf=crf)
    full_writer = H264VideoWriter(str(full_path), fps, (full_w, full_h), crf=crf)
    strip_indices = {int(round(i * (frames_total - 1) / (STRIP_FRAMES - 1))) for i in range(STRIP_FRAMES)}
    strip_images: list[np.ndarray] = []
    written = 0
    try:
        for offset, box in enumerate(boxes):
            ok, frame = capture.read()
            if not ok:
                break
            cropped = square_crop(frame, box) if box else cv2.resize(frame, (SIZE, SIZE))
            crop_writer.write(cropped)
            full_writer.write(cv2.resize(frame, (full_w, full_h), interpolation=cv2.INTER_AREA))
            if offset in strip_indices:
                label = f"{(start - 1 + offset) / fps:05.1f}s"
                canvas = cropped.copy()
                cv2.rectangle(canvas, (4, 4), (78, 20), (0, 0, 0), -1)
                cv2.putText(canvas, label, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
                strip_images.append(canvas)
            written += 1
    finally:
        crop_writer.release()
        full_writer.release()
        capture.release()

    if strip_images:
        rows = math.ceil(len(strip_images) / STRIP_COLS)
        sheet = np.full((rows * SIZE, STRIP_COLS * SIZE, 3), 24, dtype=np.uint8)
        for position, image in enumerate(strip_images):
            row, col = divmod(position, STRIP_COLS)
            sheet[row * SIZE:(row + 1) * SIZE, col * SIZE:(col + 1) * SIZE] = image
        cv2.imwrite(str(strip_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])

    return {
        "crop": str(crop_path),
        "full": str(full_path),
        "strip": str(strip_path),
        "framesWritten": written,
        "framesExpected": frames_total,
        "fps": round(as_float(fps, "帧率", 15.0), 3),
        "seconds": round(written / as_float(fps, "帧率", 15.0), 2),
        "sourceSize": [width, height],
    }


def main() -> int:
    args = parse_args()
    stem, start, end, label = parse_interval(args.sample_id)
    rows = load_rows(args.clips, args.sample_id)
    track_id = args.track_id if args.track_id is not None else rows[0].get("track_id")
    video_rel = rows[0]["video"]
    video_stem = Path(video_rel).stem
    source = args.video_root / video_rel
    track_path = args.tracks_dir / f"{video_stem}.track.json"
    if not track_path.is_file():
        raise SystemExit(f"缺少轨迹文件：{track_path}")
    try:
        payload = json.loads(track_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"轨迹文件不可用：{track_path}（{error}）") from error
    track = pick_track(payload, start, end, as_int(track_id, "track_id") if track_id is not None else None)
    frames = list(range(start, end + 1))
    deps = local_deps()
    boxes = deps["smooth"](deps["interpolate"](track.get("points", []), frames))
    prefix = args.name or f"{video_stem}__{start}-{end}"
    result = render(source, args.out, prefix, start, end, boxes, args.crf)
    summary = {
        "sample_id": args.sample_id,
        "label": label,
        "video": str(source),
        "interval": [start, end],
        "track_id": as_int(track.get("track_id", -1), "轨迹 id"),
        "trackSpecies": track.get("species"),
        "clipWindows": sorted({f'{r["start"]}-{r["end"]}' for r in rows}),
        **result,
    }
    (args.out / f"{prefix}-interval.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
