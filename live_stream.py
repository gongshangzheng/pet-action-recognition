"""Live 直播推理脚本——帧级流式推送，视频帧和推理结果走同一条 SSE。

每帧：
  1. decord 读帧
  2. mmaction2 推理（单帧 → clip 滑动窗口）
  3. SSE 同时推送 frame + inference_result
  4. 等待帧间隔（控制播放速度）

输出（SSE data 行）：
  {"type": "frame", "t": 0.0, "fps": 30.0, "width": 640, "height": 360, "data_url": "data:image/jpeg;base64,..."}
  {"type": "result", "t": 0.0, "label": "locomotion", "score": 0.92, "top5": [...], "model": "tsn-r50"}
  {"type": "status", "status": "loading_model", "model": "..."}
  {"type": "done"}
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# K400 标签映射（演示用）
DEFAULT_LABELS = str(REPO / "models" / "mmaction2" / "tools" / "data" / "kinetics" / "label_map_k400.txt")


def _encode_jpeg(frame) -> str:
    """numpy array (H,W,3) RGB → base64 JPEG data URL。"""
    import cv2
    bgr = frame[:, :, ::-1]  # RGB → BGR
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    return base64.b64encode(buf).decode("ascii")


def open_video(video: str):
    import decord
    decord.bridge.set_bridge("native")
    vr = decord.VideoReader(video, num_threads=1)
    fps = float(vr.get_avg_fps()) or 30.0
    return vr, fps, len(vr)


def load_model(model_id: str, device: str, labels: list[str]):
    from mmengine.config import Config
    from mmaction.apis import init_recognizer
    from server.routers.training import _MMACTION2_REGISTRY
    from server.config import resolve_mmaction2_config

    m = next((x for x in _MMACTION2_REGISTRY if x["id"] == model_id), None)
    if not m:
        raise ValueError(f"unknown model_id: {model_id}")

    cfg_path = resolve_mmaction2_config(m["mmaction2_config"])
    ckpt_dir = os.path.join(REPO, "checkpoints", model_id)
    # 优先用 trained checkpoint
    ckpt = os.path.join(ckpt_dir, f"{model_id}_latest.pth")
    if not os.path.isfile(ckpt):
        ckpt = os.path.join(ckpt_dir, f"{model_id}_pretrained.pth")
    if not os.path.isfile(ckpt):
        ckpt = os.path.join(ckpt_dir, [f for f in os.listdir(ckpt_dir) if f.endswith(".pth")][0])

    cfg = Config.fromfile(cfg_path)
    model = init_recognizer(cfg, ckpt, device=device)
    return model


def infer_frame(model, frame_rgb, labels: list[str]):
    """对单帧推理（构造伪 clip）。"""
    import cv2
    import numpy as np
    import torch
    from scripts._infer import _extract_topk

    # resize 到模型期望的输入尺寸
    h, w = frame_rgb.shape[:2]
    target_h, target_w = 224, 224
    resized = cv2.resize(frame_rgb, (target_w, target_h))
    # 构造 T=1 的伪 clip: (1, C, H, W)
    tensor = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
    tensor = tensor.unsqueeze(0)  # (1, 3, H, W)

    with torch.no_grad():
        scores = model.forward_dispatch(tensor, "cuda:0" if torch.cuda.is_available() else "cpu")
        if hasattr(scores, "detach"):
            scores = scores.detach().cpu()
    result = [float(s) for s in scores[0]]
    top5 = sorted(zip(result, labels), reverse=True)[:5]
    return top5


def emit(obj):
    print(json.dumps(obj), flush=True)


def main():
    ap = argparse.ArgumentParser(description="Live 直播推理：帧级流式推送")
    ap.add_argument("--video", required=True, help="视频文件绝对路径")
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--labels", default=DEFAULT_LABELS)
    ap.add_argument("--stride-sec", type=float, default=0.5, help="推理步长（秒）")
    ap.add_argument("--clip-sec", type=float, default=1.0, help="推理 clip 时长")
    args = ap.parse_args()

    if not os.path.isfile(args.video):
        emit({"type": "error", "error": f"video not found: {args.video}"})
        return 1

    from scripts._infer import load_labels
    labels = load_labels(args.labels)

    # 加载模型
    emit({"type": "status", "status": "loading_model", "model": args.model_id})
    try:
        model = load_model(args.model_id, args.device, labels)
    except Exception as e:
        emit({"type": "error", "error": f"model load failed: {e}"})
        return 1
    emit({"type": "status", "status": "model_loaded", "model": args.model_id})

    # 打开视频
    try:
        vr, fps, total = open_video(args.video)
    except Exception as e:
        emit({"type": "error", "error": f"open video failed: {e}"})
        return 1

    duration = total / fps
    frame_interval = 1.0 / fps
    last_infer_t = -999.0

    for frame_idx in range(total):
        t = frame_idx / fps
        frame = vr[frame_idx].asnumpy()  # (H,W,3) RGB

        # 推送帧
        emit({
            "type": "frame",
            "t": round(t, 3),
            "fps": round(fps, 1),
            "width": frame.shape[1],
            "height": frame.shape[0],
            "data_url": f"data:image/jpeg;base64,{_encode_jpeg(frame)}",
        })

        # 推理（按 stride）
        if t - last_infer_t >= args.stride_sec:
            last_infer_t = t
            try:
                top5 = infer_frame(model, frame, labels)
                label, score = top5[0]
                emit({
                    "type": "result",
                    "t": round(t, 3),
                    "label": label,
                    "score": round(score, 4),
                    "top5": [[l, round(s, 4)] for s, l in top5],
                    "model": args.model_id,
                })
            except Exception as e:
                emit({"type": "error", "error": f"inference failed: {e}"})

        # 控制帧率
        elapsed = frame_idx * frame_interval
        next_t = (frame_idx + 1) * frame_interval
        sleep_t = next_t - elapsed - (time.time() - time.time())  # 简单控制
        if frame_idx < total - 1:
            time.sleep(max(0, frame_interval * 0.95))  # 略快一点，留 buffer

    emit({"type": "done"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
