"""Live 实时推理脚本——同步边播边推，逐段 print JSON 到 stdout（后端转 SSE）。

借鉴 third-party/pet-videos 的 llm_worker 分析逻辑，但改为同步逐段而非事后队列。
每段：ffmpeg 切 clip 临时文件 → 推理（mmaction2 或 VLM）→ 删临时 → print JSON 行。

输出（每行一个 JSON）：
  {"t_start":0.0,"t_end":1.0,"label":"archery","score":0.83,"top5":[...],"model":"tsn-resnet50"}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DEFAULT_LABELS = str(REPO / "models" / "mmaction2" / "tools" / "data" / "kinetics" / "label_map_k400.txt")


def open_video(video: str):
    """decord VideoReader + fps + 总帧数。返回 (vr, fps, total_frames)。"""
    import decord
    decord.bridge.set_bridge("native")
    vr = decord.VideoReader(video, num_threads=1)
    fps = vr.get_avg_fps() or 0.0
    return vr, fps, len(vr)


def make_clip(vr, fps: float, total: int, t_start: float, duration: float, out_path: str) -> bool:
    """decord 取 clip 帧 + cv2.VideoWriter 写临时 mp4（不依赖 ffmpeg 二进制）。"""
    if fps <= 0:
        return False
    import cv2
    f0 = max(0, int(t_start * fps))
    f1 = min(total, int((t_start + duration) * fps))
    if f1 <= f0:
        return False
    frames = vr.get_batch(list(range(f0, f1))).asnumpy()  # (N,H,W,3) RGB
    h, w = frames.shape[1], frames.shape[2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    if not writer.isOpened():
        return False
    for fr in frames:
        writer.write(fr[:, :, ::-1])  # RGB → BGR
    writer.release()
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 0


def load_mmaction2_model(model_id: str, device: str):
    """加载 mmaction2 模型（init_recognizer，慢，调用方应缓存）。"""
    from mmengine.config import Config
    from mmaction.apis import init_recognizer
    from server.routers.training import _MMACTION2_REGISTRY
    from server.config import resolve_mmaction2_config

    m = next((x for x in _MMACTION2_REGISTRY if x["id"] == model_id), None)
    if not m:
        raise ValueError(f"unknown model_id: {model_id}")
    cfg_path = resolve_mmaction2_config(m["mmaction2_config"])
    ckpt = os.path.join(REPO, "checkpoints", model_id, f"{model_id}_pretrained.pth")
    if not os.path.isfile(ckpt):
        raise FileNotFoundError(f"checkpoint not found: {ckpt}")
    cfg = Config.fromfile(cfg_path)
    # 关掉不需要的 visualize/save
    if hasattr(cfg, "model") and hasattr(cfg.model, "init_cfg"):
        pass
    model = init_recognizer(cfg, ckpt, device=device)
    return model


def infer_clip_mmaction2(model, clip_path: str, labels: list[str]) -> list[tuple]:
    """对 clip 文件推理，返回 top5 [(label, score)]。"""
    from mmaction.apis import inference_recognizer
    from scripts._infer import _extract_topk
    result = inference_recognizer(model, clip_path)
    return _extract_topk(result, labels, k=5)


def infer_clip_vlm(clip_path: str, labels: list[str]) -> dict:
    """VLM 对 clip 调 Qwen3-VL。"""
    from scripts.vlm_infer import vlm_recognize
    return vlm_recognize(clip_path, labels)


def main() -> int:
    ap = argparse.ArgumentParser(description="Live 实时推理：逐段输出 JSON")
    ap.add_argument("--video", required=True, help="视频文件绝对路径")
    ap.add_argument("--model-id", required=True, help="registry model_id 或 vlm")
    ap.add_argument("--model-type", choices=["mmaction2", "vlm"], required=True)
    ap.add_argument("--clip-sec", type=float, default=1.0, help="每段时长（秒）")
    ap.add_argument("--stride-sec", type=float, default=1.0, help="步长（秒）")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--labels", default=DEFAULT_LABELS)
    args = ap.parse_args()

    if not os.path.isfile(args.video):
        print(json.dumps({"error": f"video not found: {args.video}"}), flush=True)
        return 1

    from scripts._infer import load_labels
    labels = load_labels(args.labels)

    # 加载模型（mmaction2 慢，加载一次复用；vlm 无状态）
    # 注意：mmaction2 init_recognizer 触发 torch CUDA init，必须在 decord open 之前，
    # 否则 decord 占用 fd 导致 torch CUDA random_device 读 /dev/urandom 失败
    model = None
    if args.model_type == "mmaction2":
        t0 = time.time()
        print(json.dumps({"status": "loading_model", "model": args.model_id}), flush=True)
        try:
            model = load_mmaction2_model(args.model_id, args.device)
        except Exception as e:
            print(json.dumps({"error": f"model load failed: {e}"}), flush=True)
            return 1
        print(json.dumps({"status": "model_loaded", "model": args.model_id, "took_sec": round(time.time() - t0, 1)}), flush=True)

    try:
        vr, fps, total = open_video(args.video)
    except Exception as e:
        print(json.dumps({"error": f"open video failed: {e}"}), flush=True)
        return 1
    duration = (total / fps) if fps > 0 else 0.0
    if duration <= 0:
        print(json.dumps({"error": "cannot read duration"}), flush=True)
        return 1

    t = 0.0
    while t < duration:
        clip_start = t
        clip_end = min(t + args.clip_sec, duration)
        clip_dur = clip_end - clip_start
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            clip_path = tf.name
        try:
            if not make_clip(vr, fps, total, clip_start, clip_dur, clip_path):
                print(json.dumps({"error": "make clip failed", "t_start": clip_start}), flush=True)
                break
            if args.model_type == "mmaction2":
                top5 = infer_clip_mmaction2(model, clip_path, labels)
                label, score = top5[0] if top5 else ("", 0.0)
            else:
                r = infer_clip_vlm(clip_path, labels)
                label = r.get("top1_label", "")
                score = r.get("top1_score", 0)
                top5 = r.get("top5", [])
            print(json.dumps({
                "t_start": round(clip_start, 2), "t_end": round(clip_end, 2),
                "label": label, "score": round(float(score), 4) if score else 0,
                "top5": [[l, round(float(s), 4)] for l, s in top5] if top5 else [],
                "model": args.model_id,
            }, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e), "t_start": clip_start}), flush=True)
        finally:
            try:
                os.unlink(clip_path)
            except OSError:
                pass
        t += args.stride_sec

    print(json.dumps({"status": "done", "segments": int(duration / args.stride_sec) + 1}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
