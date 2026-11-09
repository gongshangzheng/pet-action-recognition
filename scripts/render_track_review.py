#!/usr/bin/env python3
"""渲染轨迹叠加核对视频（multi-pet-sort-tracking 2.4）。

每个 track 一种颜色画框 + id 标签，锚点间线性插值补显示框（只为可读性，
不参与指标）。逐帧写出 H.264 视频 + 每视频核对摘要 JSON（track 清单、
逐锚点活跃轨迹数 vs pet_count）。

用法（本地 CPU）：
    python3 scripts/render_track_review.py \
        --video-dir <src> --tracks-dir <tracks> --detections-dir <dets> \
        --out results/tracking_eval_20261107/review_videos
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.videowriter import H264VideoWriter  # noqa: E402

PALETTE = [
    (0, 215, 255), (255, 140, 0), (0, 255, 0), (255, 0, 200),
    (0, 165, 255), (200, 0, 255), (0, 255, 255), (128, 255, 0),
    (255, 255, 0), (80, 172, 255), (255, 0, 128), (60, 76, 231),
]


def lerp(a, b, t: float):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def render_video(video_path: Path, track_payload: dict, det_payload: dict, out_dir: Path) -> dict:
    tracks = [t for t in track_payload["tracks"] if t["state"] == "confirmed"]
    color = {t["track_id"]: PALETTE[i % len(PALETTE)] for i, t in enumerate(tracks)}
    stride = track_payload["sample_stride"]

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_h = int(1280 * H / W)
    out_path = out_dir / f"{video_path.stem}.review.mp4"
    vw = H264VideoWriter(str(out_path), fps, (1280, out_h))

    anchor_map: dict[int, dict[int, tuple]] = {}
    for t in tracks:
        for p in t["points"]:
            anchor_map.setdefault(p["frame"], {})[t["track_id"]] = tuple(p["box"])

    fi = 0
    last_boxes: dict[int, tuple] = {}
    per_anchor_rows = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi in anchor_map:
            last_boxes = dict(anchor_map[fi])
            det_state = det_payload["anchors"].get(str(fi))
            pet_count = (
                ((det_state.get("cat_count") or 0) + (det_state.get("dog_count") or 0))
                if det_state else None
            )
            per_anchor_rows.append(
                {"frame": fi, "active_tracks": len(last_boxes), "pet_count": pet_count}
            )
        # 锚点间插值：与下一个锚点的已知框线性过渡（仅显示）
        disp = last_boxes
        if fi % stride and (fi + stride - fi % stride) in anchor_map:
            nxt = anchor_map[fi + stride - fi % stride]
            t = (fi % stride) / stride
            disp = {
                tid: lerp(last_boxes.get(tid, box), box, t)
                for tid, box in nxt.items()
            }
        for tid, box in disp.items():
            c = color.get(tid, (255, 255, 255))
            x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(frame, (x1, y1), (x2, y2), c, 2)
            cv2.putText(frame, f"id{tid}", (x1, max(12, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
        vw.write(cv2.resize(frame, (1280, out_h)))
        fi += 1
    cap.release()
    vw.release()

    return {
        "video": track_payload["video"],
        "review_video": out_path.name,
        "tracks": [
            {"track_id": t["track_id"], "species": t["species"],
             "n_anchors": t["n_anchors"], "frames": f"{t['first_frame']}-{t['last_frame']}",
             "color_bgr": color[t["track_id"]]}
            for t in tracks
        ],
        "anchor_rows": per_anchor_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", type=Path, required=True)
    parser.add_argument("--tracks-dir", type=Path, required=True)
    parser.add_argument("--detections-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    summaries = []
    for track_path in sorted(args.tracks_dir.glob("*.track.json")):
        stem = track_path.name.removesuffix(".track.json")
        video_path = args.video_dir / f"{stem}.mp4"
        if not video_path.is_file():
            print(f"[skip] no source video for {stem}")
            continue
        det_path = args.detections_dir / f"{stem}.json"
        for required in (track_path, video_path, det_path):
            if not required.is_file():
                raise FileNotFoundError(f"render_track_review: missing input {required}")
        try:
            tp = json.loads(track_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"corrupt track file {track_path}: {e}") from e
        try:
            dp = json.loads(det_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"corrupt detection file {det_path}: {e}") from e
        s = render_video(video_path, tp, dp, args.out)
        summaries.append(s)
        print(f"[render] {stem}: {len(s['tracks'])} tracks -> {s['review_video']}")

    (args.out / "review_summary.json").write_text(
        json.dumps({"schema": "multi-pet-track-review-v1", "videos": summaries},
                   ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"REVIEW DONE -> {args.out}/review_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
