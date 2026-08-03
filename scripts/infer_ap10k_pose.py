#!/usr/bin/env python3
"""MMPose AP-10K 动物骨架提取（对照 DeepLabCut SuperAnimal-Quadruped）。

top-down 流程：RTMDet(COCO 动物类) 检测 → RTMPose-m(AP-10K, 17 关键点) 姿态估计。
用于 t10-1 对照实验：在与 DLC 相同的抽检视频上生成标注视频，人工评判质量。

运行在 pet 的 `pet` conda env（mmaction2 环境，已装 mmpose/mmdet）：
  ~/miniconda3/envs/pet/bin/python scripts/infer_ap10k_pose.py \
    --videos datasets/pet_action_mammal_v0/dataset/video/AAOYRUDX.mp4 ... \
    --device cuda:1

产物（--out-dir，默认 results/skeleton/ap10k_vis/）：
  <stem>_ap10k.mp4   H.264 标注视频（检测框 + 17 点骨架 + mean conf）
  <stem>_ap10k.npz   keypoint (T,17,2) + keypoint_score (T,17) + bodyparts
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _infer import _transcode_h264  # noqa: E402

# mmdet COCO 类别索引中的动物类（0-indexed）
COCO_ANIMAL_LABELS = {14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep",
                      19: "cow", 20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe"}

DEFAULT_POSE_CFG = "checkpoints/ap10k/rtmpose-m_8xb64-210e_ap10k-256x256.py"
DEFAULT_POSE_CKPT = "checkpoints/ap10k/rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206.pth"
DEFAULT_DET_CFG = "checkpoints/ap10k/rtmdet_m_8xb32-300e_coco.py"
DEFAULT_DET_CKPT = "checkpoints/ap10k/rtmdet_m_8xb32-300e_coco_20220719_112220-229f527c.pth"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MMPose AP-10K animal pose extraction")
    p.add_argument("--videos", nargs="+", required=True)
    p.add_argument("--pose-config", default=DEFAULT_POSE_CFG)
    p.add_argument("--pose-checkpoint", default=DEFAULT_POSE_CKPT)
    p.add_argument("--det-config", default=DEFAULT_DET_CFG)
    p.add_argument("--det-checkpoint", default=DEFAULT_DET_CKPT)
    p.add_argument("--out-dir", default="results/skeleton/ap10k_vis")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--bbox-score", type=float, default=0.3)
    return p.parse_args()


def draw_frame(frame, bbox, label_name, det_score, kps, scores, links, link_colors):
    import cv2

    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(frame, f"{label_name} {det_score:.2f}", (x1, max(16, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    for a, b in links:
        if a < len(kps) and b < len(kps) and scores[a] > 0.3 and scores[b] > 0.3:
            pa, pb = (int(kps[a][0]), int(kps[a][1])), (int(kps[b][0]), int(kps[b][1]))
            cv2.line(frame, pa, pb, (0, 255, 0), 2)
    for i, (x, y) in enumerate(kps):
        if scores[i] > 0.3:
            cv2.circle(frame, (int(x), int(y)), 3, (0, 255, 255), -1)
    cv2.putText(frame, f"mean conf {scores.mean():.2f}", (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame


def process_video(video, det_model, pose_model, out_dir, bbox_thr, device):
    import cv2
    from mmengine.registry import init_default_scope
    from mmdet.apis import inference_detector
    from mmpose.apis import inference_topdown

    stem = Path(video).stem
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp_mp4v = str(out_dir / f"{stem}_ap10k_mp4v.mp4")
    writer = cv2.VideoWriter(tmp_mp4v, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    meta = getattr(pose_model, "dataset_meta", {}) or {}
    links = meta.get("skeleton_links", [])
    bodyparts = list(meta.get("keypoint_colors", {}).keys()) if isinstance(meta.get("keypoint_colors"), dict) else []

    all_kps, all_scores = [], []
    ok, frame = cap.read()
    while ok:
        init_default_scope("mmdet")
        det = inference_detector(det_model, frame)
        inst = det.pred_instances
        keep = [(i, float(inst.scores[i])) for i in range(len(inst))
                if int(inst.labels[i]) in COCO_ANIMAL_LABELS and float(inst.scores[i]) >= bbox_thr]
        if keep:
            best_i = max(keep, key=lambda t: t[1])[0]
            bbox = inst.bboxes[best_i].cpu().numpy()
            label_name = COCO_ANIMAL_LABELS[int(inst.labels[best_i])]
            det_score = float(inst.scores[best_i])
            init_default_scope("mmpose")
            preds = inference_topdown(pose_model, frame, [bbox], bbox_format="xyxy")
            if preds:
                pi = preds[0].pred_instances
                kps = np.asarray(pi.keypoints)[0]  # (17, 2)
                scores = np.asarray(pi.keypoint_scores)[0]  # (17,)
            else:
                kps = np.zeros((17, 2), dtype=np.float32)
                scores = np.zeros(17, dtype=np.float32)
            frame = draw_frame(frame, bbox, label_name, det_score, kps, scores, links, None)
        else:
            kps = np.zeros((17, 2), dtype=np.float32)
            scores = np.zeros(17, dtype=np.float32)
            cv2.putText(frame, "no animal detected", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        all_kps.append(kps.astype(np.float32))
        all_scores.append(scores.astype(np.float32))
        writer.write(frame)
        ok, frame = cap.read()

    cap.release()
    writer.release()

    out_mp4 = str(out_dir / f"{stem}_ap10k.mp4")
    _transcode_h264(tmp_mp4v, out_mp4)
    np.savez_compressed(
        out_dir / f"{stem}_ap10k.npz",
        keypoint=np.stack(all_kps) if all_kps else np.zeros((0, 17, 2), dtype=np.float32),
        keypoint_score=np.stack(all_scores) if all_scores else np.zeros((0, 17), dtype=np.float32),
        bodyparts=np.array(bodyparts if bodyparts else [f"bp{i}" for i in range(17)]),
        video=np.array(str(video)),
    )
    return out_mp4, len(all_kps)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from mmdet.apis import init_detector
    from mmpose.apis import init_model as init_pose

    det_model = init_detector(args.det_config, args.det_checkpoint, device=args.device)
    pose_model = init_pose(args.pose_config, args.pose_checkpoint, device=args.device)
    print("[info] 模型已加载", flush=True)

    for video in args.videos:
        try:
            out_mp4, n = process_video(video, det_model, pose_model, out_dir, args.bbox_score, args.device)
            print(f"[ok] {Path(video).stem}: {n} 帧 -> {out_mp4}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[error] {Path(video).stem}: {type(e).__name__}: {e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
