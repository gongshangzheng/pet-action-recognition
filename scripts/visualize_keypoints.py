#!/usr/bin/env python3
"""关键点可视化抽查：把 NPZ 关键点叠加到视频帧上，人工核对 27→17 映射质量。

用法：
    python3 scripts/visualize_keypoints.py \
        --npz datasets/pet_action_mammal_v0/skeleton/kp_npz/<stem>.npz \
        --video <对应视频文件> --out /tmp/kp_vis --frames 0,30,60
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("/tmp/kp_vis"))
    parser.add_argument("--frames", default="0,30,60", help="逗号分隔帧号")
    parser.add_argument("--min-score", type=float, default=0.3)
    args = parser.parse_args()

    data = np.load(args.npz, allow_pickle=True)
    kp = data["keypoints"]  # (T, K, 2) 原始 SuperAnimal 点位（非 canon 17）
    parts = json.loads(str(data["bodyparts"]))
    scores = data["scores"]
    args.out.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(args.video))
    for f in [int(x) for x in args.frames.split(",")]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, frame = cap.read()
        if not ok:
            print(f"frame {f}: read fail")
            continue
        if f >= kp.shape[0]:
            print(f"frame {f}: beyond npz T={kp.shape[0]}")
            continue
        for i, part in enumerate(parts):
            x, y = kp[f, i]
            s = scores[f, i]
            color = (0, 255, 0) if s >= args.min_score else (0, 0, 255)
            cv2.circle(frame, (int(x), int(y)), 4, color, -1)
            cv2.putText(frame, f"{part}:{s:.2f}", (int(x) + 5, int(y) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
        out_path = args.out / f"{args.npz.stem}_frame{f:05d}.jpg"
        cv2.imwrite(str(out_path), frame)
        print(f"wrote {out_path}")
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
