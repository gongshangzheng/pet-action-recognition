"""三联跟随视角对比视频：左=原始帧，右上=interp-only，右下=motion-corrected。

batch-followcam-extraction 任务 1.2 验收辅助（design B2）。
左右布局：左侧原始画面（叠加两版取景框示意），右侧上下两路跟随视角裁剪：
  - 右上：仅插值（nc track.json 的 box）
  - 右下：运动校正（mc track.json 的 camera_box，无则退回 box）

用法（pet plf 环境）：
  python scripts/plf_compare_followcam3.py --video <mp4> \
      --nc results/X_nc/track.json --mc results/X_mc/track.json \
      --out results/X_mc/compare3.mp4
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

PANEL = 480        # 右侧单路跟随视角尺寸（正方形）
GAP = 8            # 面板间距
BLUE = (255, 120, 0)   # interp-only
GREEN = (0, 255, 0)    # motion-corrected
PAD = 1.2          # 跟随裁剪外扩系数（与管线 follow_adaptive 一致）


def crop_square(frame: np.ndarray, box: list[float]) -> np.ndarray:
    H, W = frame.shape[:2]
    x1, y1, x2, y2 = box
    side = max(x2 - x1, y2 - y1) * PAD
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    xa, ya = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    xb, yb = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
    crop = frame[ya:yb, xa:xb]
    if crop.size == 0:
        return np.zeros((PANEL, PANEL, 3), np.uint8)
    return cv2.resize(crop, (PANEL, PANEL))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--nc", required=True)
    ap.add_argument("--mc", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    nc = json.load(open(args.nc))["smooth_track"]
    mc = json.load(open(args.mc))["smooth_track"]
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    right_h = PANEL * 2 + GAP
    left_w = int(W * right_h / H)
    left_w -= left_w % 2
    total_w = left_w + GAP + PANEL
    total_h = right_h - (right_h % 2)
    vw = H264VideoWriter(args.out, fps, (total_w, total_h))

    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        b1 = nc[min(fi, len(nc) - 1)]["box"]
        m2 = mc[min(fi, len(mc) - 1)]
        b2 = m2.get("camera_box", m2["box"])

        # 左：原始画面（缩放到右列高度），叠加两路取景框
        left = cv2.resize(frame, (left_w, right_h))
        sx = left_w / W
        sy = right_h / H
        cv2.rectangle(left, (int(b1[0]*sx), int(b1[1]*sy)),
                      (int(b1[2]*sx), int(b1[3]*sy)), BLUE, 2)
        cv2.rectangle(left, (int(b2[0]*sx), int(b2[1]*sy)),
                      (int(b2[2]*sx), int(b2[3]*sy)), GREEN, 2)
        cv2.putText(left, "original", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        # 右上：interp-only 跟随；右下：motion-corrected 跟随
        top = crop_square(frame, b1)
        bot = crop_square(frame, b2)
        cv2.putText(top, "interp-only", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, BLUE, 2)
        cv2.putText(bot, "motion-corrected", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, GREEN, 2)

        right_col = np.vstack([top, np.full((GAP, PANEL, 3), 30, np.uint8), bot])
        canvas = np.full((total_h, total_w, 3), 30, np.uint8)
        canvas[:right_h, :left_w] = left
        canvas[:PANEL, left_w + GAP:left_w + GAP + PANEL] = top
        y0 = PANEL + GAP
        canvas[y0:y0 + PANEL, left_w + GAP:left_w + GAP + PANEL] = bot
        vw.write(canvas)
        fi += 1
    vw.release()
    cap.release()
    print(f"frames={fi} -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
