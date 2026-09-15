"""轨迹运动校正消融对比：仅插值 vs 插值+帧差校正，同屏画框 + 差异统计。

batch-followcam-extraction 任务 1.2 验收脚本（design B2）。
输入同一视频的两份 track.json（--no-motion-correct 版 vs 默认版），
蓝框=仅插值，绿框=插值+校正；输出 H.264 对比视频 + 差异统计 JSON。

用法（pet plf 环境）：
  python scripts/plf_compare_track_correction.py --video <mp4> \
      --nc results/X_nc/track.json --mc results/X_mc/track.json \
      --out results/X_mc/compare.mp4
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--nc", required=True, help="仅插值版 track.json")
    ap.add_argument("--mc", required=True, help="插值+校正版 track.json")
    ap.add_argument("--out", required=True, help="输出对比视频路径")
    ap.add_argument("--width", type=int, default=1280)
    args = ap.parse_args()

    nc = json.load(open(args.nc))["smooth_track"]
    mc = json.load(open(args.mc))["smooth_track"]
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    oh = int(args.width * H / W)
    oh -= oh % 2  # H.264 要求偶数尺寸
    vw = H264VideoWriter(args.out, fps, (args.width, oh))

    fi, difs = 0, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        vis = cv2.resize(frame, (args.width, oh))
        sx = args.width / W
        b1 = nc[min(fi, len(nc) - 1)]["box"]
        m2 = mc[min(fi, len(mc) - 1)]
        b2 = m2.get("camera_box", m2["box"])  # 优先画相机路径（渲染框）
        difs.append(float(np.abs(np.array(b1) - np.array(b2)).mean()))
        cv2.rectangle(vis, (int(b1[0]*sx), int(b1[1]*sx)),
                      (int(b1[2]*sx), int(b1[3]*sx)), (255, 120, 0), 3)
        cv2.rectangle(vis, (int(b2[0]*sx), int(b2[1]*sx)),
                      (int(b2[2]*sx), int(b2[3]*sx)), (0, 255, 0), 3)
        cv2.putText(vis, "interp-only", (int(b1[0]*sx), max(24, int(b1[1]*sx) - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 120, 0), 2)
        cv2.putText(vis, "motion-corrected", (int(b2[0]*sx), max(56, int(b2[1]*sx) - 34)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        vw.write(vis)
        fi += 1
    vw.release()
    cap.release()
    d = np.array(difs)
    stats = {"frames": fi, "mean_box_diff_px": round(float(d.mean()), 1),
             "p95": round(float(np.percentile(d, 95)), 1), "max": round(float(d.max()), 1)}
    json.dump(stats, open(f"{args.out}.json", "w"), indent=2)
    print(f"frames={fi} mean={stats['mean_box_diff_px']}px p95={stats['p95']}px max={stats['max']}px")


if __name__ == "__main__":
    main()
