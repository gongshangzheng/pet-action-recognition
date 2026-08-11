"""模型推理速度 + 大小基准。

加载模型一次（不计入时间），对 N 个 val 视频跑推理，测：
- latency_ms：每视频平均推理时间（不含模型加载）
- fps：每秒处理视频数
- rtf：推理时间 / 视频时长（<1 表示比实时快）
- gpu_mem_mb：推理峰值显存
- param_count：模型参数量（M）
- ckpt_size_mb：checkpoint 文件大小

可作模块导入（benchmark()）或 CLI 独立运行（对已有 checkpoint 补测，不重训）。

用法：
  python scripts/benchmark_speed.py --model-id videomaev2-base \
    --run-id trainall-... --mmaction2-config configs/... --num-videos 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import resolve_mmaction2_config, CHECKPOINTS_DIR  # noqa: E402


def _read_val_videos(ann_file: str, data_root: str, n: int) -> list[tuple[str, int]]:
    """从 val ann_file 取前 n 个 (rel_path, label)。"""
    out = []
    with open(ann_file) as f:
        for ln in f:
            parts = ln.strip().split()
            if len(parts) < 2:
                continue
            rel, lab = parts[0], int(parts[1])
            full = rel if os.path.isabs(rel) else os.path.join(data_root, rel)
            if os.path.isfile(full):
                out.append((full, lab))
            if len(out) >= n:
                break
    return out


# 视频时长 mtime 缓存（移植自 pet-videos video_cache；避免重复 cv2 读元信息）
_DURATION_CACHE: dict[str, tuple[float, float]] = {}


def _video_duration(video_path: str) -> float:
    import os, cv2
    try:
        mtime = os.path.getmtime(video_path)
    except OSError:
        mtime = 0
    cached = _DURATION_CACHE.get(video_path)
    if cached and cached[0] == mtime:
        return cached[1]
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    dur = (n / fps) if fps > 0 and n > 0 else 0.0
    _DURATION_CACHE[video_path] = (mtime, dur)
    return dur


def _param_count(model) -> int:
    """统计模型总参数量。"""
    try:
        import torch
        if hasattr(model, "module"):
            model = model.module
        return sum(p.numel() for p in model.parameters())
    except Exception:
        return 0


def benchmark(
    cfg_path: str,
    checkpoint: str,
    ann_file: str,
    data_root: str,
    num_videos: int = 5,
    device: str = "cuda:0",
) -> dict:
    """对 model+ckpt 跑推理基准，返回 {latency_ms, fps, rtf, gpu_mem_mb, param_count_m, ckpt_size_mb}。"""
    from mmaction.apis import init_recognizer, inference_recognizer
    import torch

    videos = _read_val_videos(ann_file, data_root, num_videos)
    if not videos:
        return {"error": "no val videos found", "ann_file": ann_file, "data_root": data_root}

    cfg_abs = cfg_path if os.path.isabs(cfg_path) else resolve_mmaction2_config(cfg_path)
    model = init_recognizer(cfg_abs, checkpoint, device=device)
    param_count = _param_count(model)

    dev = torch.device(device)
    is_cuda = torch.cuda.is_available() and dev.type == "cuda"
    if is_cuda:
        torch.cuda.reset_peak_memory_stats(dev)

    # warmup 1 视频（不计时），让 CUDA kernel / 缓存就绪
    try:
        inference_recognizer(model, videos[0][0])
    except Exception:
        pass
    if is_cuda:
        torch.cuda.synchronize(dev)

    latencies, durations = [], []
    for vpath, _ in videos:
        vdur = _video_duration(vpath)
        if is_cuda:
            torch.cuda.synchronize(dev)
        t0 = time.perf_counter()
        try:
            inference_recognizer(model, vpath)
        except Exception as e:
            return {"error": f"inference failed: {e}", "video": vpath}
        if is_cuda:
            torch.cuda.synchronize(dev)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        durations.append(vdur)

    total = sum(latencies)
    n = len(latencies)
    avg_latency_ms = round(total / n * 1000, 1)
    fps = round(n / total, 2) if total > 0 else None
    rtf = round(total / sum(durations), 3) if sum(durations) > 0 else None
    gpu_mem_mb = None
    if is_cuda:
        gpu_mem_mb = round(torch.cuda.max_memory_allocated(dev) / 1e6, 1)

    ckpt_size_mb = round(os.path.getsize(checkpoint) / 1e6, 1) if os.path.isfile(checkpoint) else None

    return {
        "latency_ms": avg_latency_ms,
        "fps": fps,
        "rtf": rtf,
        "gpu_mem_mb": gpu_mem_mb,
        "param_count_m": round(param_count / 1e6, 2),
        "ckpt_size_mb": ckpt_size_mb,
        "num_videos": n,
        "device": device,
    }


def _resolve_ckpt(model_id: str, run_id: str | None) -> str | None:
    """从 checkpoints/<model>/<run>_best.pth 或 pretrained 找 checkpoint。"""
    if run_id:
        p = os.path.join(CHECKPOINTS_DIR, model_id, f"{run_id}_best.pth")
        if os.path.isfile(p):
            return os.path.realpath(p)
    # pretrained
    pre = os.path.join(CHECKPOINTS_DIR, model_id, f"{model_id}_pretrained.pth")
    return pre if os.path.isfile(pre) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--run-id", default=None, help="run_id → 用其 best ckpt；不给则用 pretrained")
    ap.add_argument("--mmaction2-config", required=True)
    ap.add_argument("--ann-file", default="datasets/pet_action_mammal_v0/annotation/val_public.txt")
    ap.add_argument("--data-root", default="datasets/pet_action_mammal_v0")
    ap.add_argument("--num-videos", type=int, default=5)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out-json", default=None, help="写到文件；不给出到 stdout")
    args = ap.parse_args()

    ckpt = _resolve_ckpt(args.model_id, args.run_id)
    if not ckpt:
        print(json.dumps({"error": "no checkpoint found", "model_id": args.model_id, "run_id": args.run_id}))
        return 1

    res = benchmark(args.mmaction2_config, ckpt, args.ann_file, args.data_root, args.num_videos, args.device)
    res["model_id"] = args.model_id
    res["run_id"] = args.run_id
    res["checkpoint"] = ckpt
    out = json.dumps(res, ensure_ascii=False, indent=2)
    if args.out_json:
        with open(args.out_json, "w") as f:
            f.write(out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
