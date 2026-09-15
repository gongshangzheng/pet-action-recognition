"""跟随视角视频渲染器：track.json（camera_box）→ 猫居中 followcam.mp4。

batch-followcam-extraction 任务 1.3。每帧按 camera_box 裁出以猫为中心的
正方形区域（外扩 1.2 倍，follow_adaptive 口径），缩放到 512×512，
H.264 直写。可选 --sbs 输出「左原始+右跟随」并排对比视频。

用法（pet plf 环境）：
  python scripts/make_followcam.py --video <mp4> \
      --track results/<段>/track.json --out results/<段>/ [--sbs]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from petlib.videowriter import H264VideoWriter  # noqa: E402

PAD = 1.2  # 裁剪外扩系数（follow_adaptive 口径）


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--sbs", action="store_true", help="同时输出并排对比视频")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    track = json.load(open(args.track))["smooth_track"]
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    sbs_h = 480
    sbs_w = int(W * sbs_h / H)
    sbs_w -= sbs_w % 2
    vw_sbs = (H264VideoWriter(f"{args.out}/side_by_side.mp4", fps,
                              (sbs_w + args.size + 8, sbs_h)) if args.sbs else None)
    vw = H264VideoWriter(f"{args.out}/followcam.mp4", fps, (args.size, args.size))

    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rec = track[min(fi, len(track) - 1)]
        bx = rec.get("camera_box", rec["box"])
        x1, y1, x2, y2 = [int(v) for v in bx]
        side = max(x2 - x1, y2 - y1) * PAD
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        xa, ya = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
        xb, yb = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
        crop = frame[ya:yb, xa:xb]
        crop = (cv2.resize(crop, (args.size, args.size))
                if crop.size else np.zeros((args.size, args.size, 3), np.uint8))
        vw.write(crop)
        if vw_sbs:
            small = cv2.resize(frame, (sbs_w, sbs_h))
            sc = sbs_w / W
            cv2.rectangle(small, (int(bx[0]*sc), int(bx[1]*sc)),
                          (int(bx[2]*sc), int(bx[3]*sc)), (0, 255, 0), 2)
            canvas = np.full((sbs_h, sbs_w + args.size + 8, 3), 30, np.uint8)
            canvas[:, :sbs_w] = small
            canvas[:, sbs_w + 8:] = crop
            vw_sbs.write(canvas)
        fi += 1
        if fi % 500 == 0:
            print(f"...{fi}", flush=True)
    vw.release()
    if vw_sbs:
        vw_sbs.release()
    cap.release()
    print(f"frames={fi} -> {args.out}/followcam.mp4", flush=True)


if __name__ == "__main__":
    main()
