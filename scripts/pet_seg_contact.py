"""告警段诊断接触表：抽样帧缩略图网格，绿=检出/红=漏检。

batch-followcam-extraction 任务 1.6 告警段排查辅助。
读取 track.json 的 sampled_detections（含检出的抽样帧集合），
对原始视频每 step 帧取缩略图：检出帧绿框+置信度，漏检帧红框 NO-DET。
输出单张长图 jpg。

用法（pet plf 环境）：
  python scripts/pet_seg_contact.py --video <mp4> --track <track.json> \
      --out <seg_contact.jpg> [--step 30]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

THUMB = 160
PER_ROW = 6
GREEN = (0, 255, 0)
RED = (0, 0, 255)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--step", type=int, default=30)
    args = ap.parse_args()

    track = json.load(open(args.track))
    detected = {int(k) for k in track.get("sampled_detections", {})}
    confs = {int(k): v.get("cat_conf", 0) for k, v in
             track.get("sampled_detections", {}).items()}

    cap = cv2.VideoCapture(args.video)
    thumbs: list[np.ndarray] = []
    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % args.step == 0:
            th = cv2.resize(frame, (THUMB, THUMB))
            hit = fi in detected
            color = GREEN if hit else RED
            cv2.rectangle(th, (0, 0), (THUMB - 1, THUMB - 1), color, 4)
            tag = f"f{fi} {confs.get(fi, 0):.2f}" if hit else f"f{fi} NO-DET"
            cv2.putText(th, tag, (4, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, color, 1)
            thumbs.append(th)
        fi += 1
    cap.release()
    if not thumbs:
        print(f"ERROR: 视频无帧可读: {args.video}", flush=True)
        sys.exit(1)

    rows = []
    for r in range(0, len(thumbs), PER_ROW):
        row = thumbs[r:r + PER_ROW]
        while len(row) < PER_ROW:
            row.append(np.full((THUMB, THUMB, 3), 30, np.uint8))
        rows.append(np.hstack(row))
    grid = np.vstack(rows)
    cv2.imwrite(args.out, grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"thumbs={len(thumbs)} -> {args.out}")


if __name__ == "__main__":
    main()
