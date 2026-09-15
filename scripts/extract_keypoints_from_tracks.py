"""关键点提取（crop-first，辅助信号）：相机路径裁剪 → HRNet-AP10K → NPZ + 叠加视频。

batch-followcam-extraction 任务 1.3。输入原始视频 + track.json（取 camera_box），
逐帧裁剪出跟随视角（512×512），HRNet-W32-AP10K 推理 17 关键点，产出：
  <out>/followcam.mp4      跟随视角视频（干净版，H.264）
  <out>/keypoints.npz      keypoints (T,17,3) float16（x,y,score，512 裁剪坐标系）+ frame_inds
  <out>/kp_overlay.mp4     骨架叠加视频（--overlay 开启时）
  stdout                   质量统计（整体/逐点置信度）

用法（pet plf 环境；GPU 任务前须 nvidia-smi 查占用）：
  CUDA_VISIBLE_DEVICES=0 python scripts/extract_keypoints_from_tracks.py \
      --video <mp4> --track results/<段>/track.json --out results/<段>/kp/ \
      [--overlay]
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

DEFAULT_CONFIG = os.path.expanduser(
    "~/models/ap10k/td-hm_hrnet-w32_8xb64-210e_ap10k-256x256.py")
DEFAULT_CKPT = os.path.expanduser(
    "~/models/ap10k/hrnet_w32_ap10k_256x256-18aac840_20211029.pth")

# AP-10K 17 点官方拓扑（mmpose .mim datasets/ap10k.py）
KP_NAMES = ['L_Eye', 'R_Eye', 'Nose', 'Neck', 'Root_of_tail', 'L_Shoulder',
            'L_Elbow', 'L_F_Paw', 'R_Shoulder', 'R_Elbow', 'R_F_Paw',
            'L_Hip', 'L_Knee', 'L_B_Paw', 'R_Hip', 'R_Knee', 'R_B_Paw']
IDX = {n: i for i, n in enumerate(KP_NAMES)}
LIMBS = [(IDX[a], IDX[b]) for a, b in [
    ('L_Eye', 'R_Eye'), ('L_Eye', 'Nose'), ('R_Eye', 'Nose'), ('Nose', 'Neck'),
    ('Neck', 'Root_of_tail'), ('Neck', 'L_Shoulder'), ('L_Shoulder', 'L_Elbow'),
    ('L_Elbow', 'L_F_Paw'), ('Neck', 'R_Shoulder'), ('R_Shoulder', 'R_Elbow'),
    ('R_Elbow', 'R_F_Paw'), ('Root_of_tail', 'L_Hip'), ('L_Hip', 'L_Knee'),
    ('L_Knee', 'L_B_Paw'), ('Root_of_tail', 'R_Hip'), ('R_Hip', 'R_Knee'),
    ('R_Knee', 'R_B_Paw')]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--overlay", action="store_true", help="同时输出骨架叠加视频")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    from mmpose.apis import init_model, inference_topdown

    model = init_model(args.config, args.ckpt, device="cuda:0")
    track = json.load(open(args.track))["smooth_track"]

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    vw = H264VideoWriter(f"{args.out}/followcam.mp4", fps, (args.size, args.size))
    vw_ov = (H264VideoWriter(f"{args.out}/kp_overlay.mp4", fps, (args.size, args.size))
             if args.overlay else None)

    SZ = args.size
    kps_all = np.zeros((len(track), len(KP_NAMES), 3), dtype=np.float16)
    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rec = track[min(fi, len(track) - 1)]
        bx = rec.get("camera_box", rec["box"])
        x1, y1, x2, y2 = [int(max(0, v)) for v in bx]
        H, W = frame.shape[:2]
        x2, y2 = min(x2, W), min(y2, H)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            black = np.zeros((SZ, SZ, 3), np.uint8)
            vw.write(black)
            if vw_ov:
                vw_ov.write(black)
            fi += 1
            continue
        crop_r = cv2.resize(crop, (SZ, SZ))
        r = inference_topdown(model, crop_r,
                              bboxes=np.array([[0, 0, SZ, SZ]], dtype=np.float32))
        pi = r[0].pred_instances
        kps = pi.keypoints[0]
        sc = pi.keypoint_scores[0]
        kps_all[fi, :, :2] = kps.astype(np.float16)
        kps_all[fi, :, 2] = sc.astype(np.float16)

        vis = crop_r.copy()
        for a, b in LIMBS:
            if sc[a] > 0.3 and sc[b] > 0.3:
                pa, pb = kps[a], kps[b]
                cv2.line(vis, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])),
                         (255, 200, 0), 2)
        for (x, y), s in zip(kps, sc):
            c = (0, 255, 0) if s > 0.5 else (0, 165, 255) if s > 0.2 else (0, 0, 255)
            cv2.circle(vis, (int(x), int(y)), 5, c, -1)
        cv2.putText(vis, f"f{fi} conf={sc.mean():.2f}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        vw.write(crop_r)
        if vw_ov:
            vw_ov.write(vis)
        fi += 1
        if fi % 300 == 0:
            print(f"...{fi}", flush=True)
    vw.release()
    if vw_ov:
        vw_ov.release()
    cap.release()

    kps_all = kps_all[:fi]
    np.savez_compressed(
        f"{args.out}/keypoints.npz",
        keypoints=kps_all,
        frame_inds=np.arange(fi),
        total_frames=fi,
        source="hrnet_w32_ap10k_cropfirst_camera_path",
        kp_names=json.dumps(KP_NAMES),
    )

    conf = kps_all[:, :, 2].astype(np.float32)
    per_kp = conf.mean(axis=0)
    order = np.argsort(per_kp)
    print(f"frames={fi} mean_conf={conf.mean():.3f} "
          f"| frames conf>0.3: {(conf.mean(axis=1) > 0.3).mean():.1%} "
          f"| >0.5: {(conf.mean(axis=1) > 0.5).mean():.1%}", flush=True)
    print("worst5:", {KP_NAMES[i]: round(float(per_kp[i]), 2) for i in order[:5]},
          flush=True)
    print("best5:", {KP_NAMES[i]: round(float(per_kp[i]), 2) for i in order[-5:]},
          flush=True)


if __name__ == "__main__":
    main()
