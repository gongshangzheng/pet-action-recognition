"""把亮点抓取载荷（需 --include-samples）叠加回视频，便于人工核对。

输出：
- <out>.mp4：按采样帧率逐帧绘制宠物框（绿）、猫脸框（红）与指标文字
- <out>_sheet.jpg：均匀抽取若干帧的拼图

用法：
  python scripts/render_highlight_demo.py --payload results/highlights/demo/x.json \
      --out results/highlights/demo/x_vis [--sheet-frames 12] [--no-video]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

GREEN, RED, WHITE, BLACK = (60, 200, 60), (40, 40, 230), (255, 255, 255), (0, 0, 0)


def put(img, text, org, scale=0.55):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, BLACK, 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, WHITE, 1, cv2.LINE_AA)


def draw(frame, s, face_segments):
    for b in s["pet_boxes"]:
        cv2.rectangle(frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), GREEN, 2)
    for b in s["face_boxes"]:
        cv2.rectangle(frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), RED, 2)
    in_face_seg = any(a <= s["t"] < e for a, e in face_segments)
    act = "-" if s["activity"] is None else f"{s['activity']:.3f}"
    lines = [
        f"t={s['t']:.1f}s  bright={s['brightness']:.2f}  contrast={s['contrast']:.2f}",
        f"pets={s['n_pets']}  body={s['body_ratio']:.3f}  activity={act}",
        f"faces={s['n_faces']}  face={s['face_ratio']:.4f}  face_seg={'Y' if in_face_seg else 'N'}",
    ]
    for i, line in enumerate(lines):
        put(frame, line, (10, 24 + 22 * i))
    return frame


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--out", required=True, help="输出前缀（不含扩展名）")
    ap.add_argument("--sheet-frames", type=int, default=12)
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    p = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    samples = p.get("samples")
    if not samples:
        raise SystemExit("payload has no samples; rerun extraction with --include-samples")
    by_frame = {s["frame"]: s for s in samples}
    size = tuple(p["analysis"]["analysis_size"])
    face_segments = p["segments"]["face_exposed"]
    sheet_idx = set(np.linspace(0, len(samples) - 1, args.sheet_frames).round().astype(int).tolist())
    sheet_frames = {samples[i]["frame"] for i in sheet_idx}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    if not args.no_video:
        writer = cv2.VideoWriter(str(out.with_suffix(".mp4")), cv2.VideoWriter_fourcc(*"mp4v"),
                                 p["analysis"]["analysis_fps"], size)
    cap = cv2.VideoCapture(p["source"]["video"])
    tiles, idx = [], 0
    last = max(by_frame)
    while idx <= last:
        if idx in by_frame:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            frame = draw(frame, by_frame[idx], face_segments)
            if writer is not None:
                writer.write(frame)
            if idx in sheet_frames:
                tiles.append(cv2.resize(frame, (size[0] // 2, size[1] // 2)))
        elif not cap.grab():
            break
        idx += 1
    cap.release()
    if writer is not None:
        writer.release()
    cols = 3
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    cv2.imwrite(str(out.parent / f"{out.name}_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"RENDER DONE -> {out}{'' if args.no_video else '.mp4'} + {out.name}_sheet.jpg", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
