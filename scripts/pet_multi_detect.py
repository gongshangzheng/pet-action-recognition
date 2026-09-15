"""GroundingDINO 多目标检测验收脚本（任务 4.1/4.2/4.3）。

一次前向检测多类物体（默认五类：cat/bed/table/sofa/shelf，--prompt 可调），逐类着色打框，
叠加空间关系状态（猫脚底点落入家具框 → "cat on X"，1.5s 迟滞防抖），
输出 H.264 验收视频 + 检出统计 JSON。

注：bowl/camera 曾因文本检测效果差从默认清单撤下（2026-09-14 用户裁定），
静态小物体走 D9 路线（SAM 一次分割 + 固定机位缓存 + 登记照检索）。

用法（在 pet 的 plf 环境执行，GPU 任务前须 nvidia-smi 查占用）：
    CUDA_VISIBLE_DEVICES=0 python scripts/plf_multi_detect.py \
        --video /path/to/event.mp4 --out results/gate4_v2/

产物：
    <out>/multi_detect.mp4   验收视频（框 + 标签 + 状态行）
    <out>/multi_detect.json  检出统计（各类检出帧数）
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from petlib.videowriter import H264VideoWriter  # noqa: E402

# 验收通过的五类清单（v1）；bowl/camera 因文本检测效果差已撤下（2026-09-14 用户裁定），
# 静态小物体走 D9 路线：SAM 一次分割 + 固定机位缓存 + 定期重分割 + 登记照检索。
DEFAULT_PROMPT = "cat. bed. table. sofa. shelf."
LABELS = ["cat", "bed", "table", "sofa", "shelf"]
COLORS = {
    "cat": (0, 255, 0), "bed": (255, 180, 0), "table": (0, 180, 255),
    "sofa": (180, 0, 255), "shelf": (255, 255, 0),
}
MODEL_ID = "IDEA-Research/grounding-dino-tiny"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT,
                    help="GroundingDINO 多 prompt（点号分隔；默认=验收五类）")
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--width", type=int, default=1280, help="输出视频宽度")
    ap.add_argument("--hold-sec", type=float, default=1.5, help="状态切换迟滞秒数")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    from transformers import AutoProcessor, GroundingDinoForObjectDetection

    device = "cuda:0"
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = GroundingDinoForObjectDetection.from_pretrained(MODEL_ID).to(device).eval()

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_h = int(args.width * H / W)
    vw = H264VideoWriter(f"{args.out}/multi_detect.mp4", fps, (args.width, out_h))

    def infer(frame: np.ndarray) -> list[tuple[str, float, np.ndarray]]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = processor(images=rgb, text=args.prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**inputs)
        res = processor.post_process_grounded_object_detection(
            out, inputs.input_ids, box_threshold=args.threshold,
            text_threshold=args.threshold,
            target_sizes=[(frame.shape[0], frame.shape[1])],
        )[0]
        return [
            (lab, float(sc), box)
            for box, sc, lab in zip(
                res["boxes"].cpu().numpy(), res["scores"].cpu().numpy(), res["labels"]
            )
        ]

    state = "unknown"
    pending, pending_cnt = None, 0
    min_hold = int(fps * args.hold_sec)
    stats: dict[str, int] = {k: 0 for k in LABELS}

    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        dets = infer(frame)
        cats = [d for d in dets if d[0] == "cat"]
        furn = [d for d in dets if d[0] != "cat"]
        for lab, _, _ in dets:
            stats[lab] = stats.get(lab, 0) + 1

        cur = "on floor"
        if cats:
            cb = max(cats, key=lambda d: d[1])[2]
            foot = ((cb[0] + cb[2]) / 2, cb[3])  # 底边中点（脚部）
            for lab, _, fb in furn:
                if fb[0] <= foot[0] <= fb[2] and fb[1] <= foot[1] <= fb[3]:
                    cur = f"cat on {lab}"
                    break
        if cur == state:
            pending, pending_cnt = None, 0
        else:
            if pending == cur:
                pending_cnt += 1
            else:
                pending, pending_cnt = cur, 1
            if pending_cnt >= min_hold:
                state = cur

        vis = cv2.resize(frame, (args.width, out_h))
        sx = args.width / W
        for lab, sc, b in dets:
            x1, y1, x2, y2 = [int(v * sx) for v in b]
            c = COLORS.get(lab, (255, 255, 255))
            cv2.rectangle(vis, (x1, y1), (x2, y2), c, 3)
            cv2.putText(vis, f"{lab} {sc:.2f}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, c, 2)
        cv2.putText(vis, f"state: {state}", (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)
        vw.write(vis)
        fi += 1
        if fi % 200 == 0:
            print(f"...{fi}", flush=True)

    vw.release()
    cap.release()
    report = {"video": args.video, "frames": fi, "threshold": args.threshold,
              "prompt": args.prompt, "det_counts": stats}
    with open(f"{args.out}/multi_detect.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"frames={fi} det_counts={stats}", flush=True)


if __name__ == "__main__":
    main()
