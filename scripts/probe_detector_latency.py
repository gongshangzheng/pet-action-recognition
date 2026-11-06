#!/usr/bin/env python3
"""检测器延迟探测（gdino-distill-yolo-detector 2.2）。

用 COCO 预训练权重（**不训练、不使用本域标注**）在同一批真实帧上测端到端耗时，
用于在学生训练前选定型号与输入分辨率的起跑档。

端到端 = ultralytics 的 predict 全流程（letterbox 预处理 + 前向 + NMS + 后处理），
不是纯前向；这样测出的数字才能与 GroundingDINO 的 0.15 s/锚点 对比。

用法（在 pet 的 yolo 环境、GPU 守卫下执行）：
    python3 scripts/probe_detector_latency.py \
        --videos /path/a.mp4 /path/b.mp4 --frames-per-video 50 \
        --models /path/yolo11n.pt /path/yolo11s.pt \
        --imgsz 640 960 1280 --out results/latency_probe/probe.json
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

import cv2
import torch


def collect_frames(videos: list[Path], per_video: int) -> list:
    """按固定间隔从每个视频取若干帧，覆盖不同场景而非集中在开头。"""
    frames = []
    for path in videos:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        if total <= 0:
            cap.release()
            raise RuntimeError(f"cannot read frame count: {path}")
        step = max(1, total // per_video)
        indices = list(range(0, total, step))[:per_video]
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, img = cap.read()
            if not ok:
                break
            frames.append(img)
        cap.release()
    return frames


def probe(model_path: Path, imgsz: int, frames: list, warmup: int, device: str) -> dict:
    # ultralytics 只装在目标机器（pet 的 yolo 环境），本地无法静态解析
    yolo_cls = importlib.import_module("ultralytics").YOLO

    model = yolo_cls(str(model_path))
    model.to(device)

    for i in range(min(warmup, len(frames))):
        model.predict(frames[i], imgsz=imgsz, device=device, verbose=False)

    torch.cuda.reset_peak_memory_stats() if device.startswith("cuda") else None
    times = []
    n_boxes = 0
    for img in frames:
        t0 = time.perf_counter()
        res = model.predict(img, imgsz=imgsz, device=device, verbose=False)
        times.append(time.perf_counter() - t0)
        if res and res[0].boxes is not None:
            n_boxes += len(res[0].boxes)

    peak_mb = (torch.cuda.max_memory_allocated() / 1024**2) if device.startswith("cuda") else None
    times.sort()
    return {
        "model": model_path.name,
        "imgsz": imgsz,
        "frames": len(times),
        "ms_p50": round(statistics.median(times) * 1000, 2),
        "ms_p90": round(times[int(len(times) * 0.9) - 1] * 1000, 2),
        "ms_mean": round(statistics.mean(times) * 1000, 2),
        "fps": round(1.0 / statistics.mean(times), 1),
        "boxes_per_frame": round(n_boxes / max(1, len(times)), 2),
        "peak_gpu_mb": None if peak_mb is None else round(peak_mb, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--videos", nargs="+", type=Path, required=True)
    ap.add_argument("--frames-per-video", type=int, default=50)
    ap.add_argument("--models", nargs="+", type=Path, required=True)
    ap.add_argument("--imgsz", nargs="+", type=int, default=[640])
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--threads", type=int, default=4, help="限制 CPU 线程数，避免触发共享机守卫")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    for env in ("OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[env] = str(args.threads)
    torch.set_num_threads(args.threads)

    frames = collect_frames(args.videos, args.frames_per_video)
    if not frames:
        raise RuntimeError("no frames collected")
    print(f"[probe] frames={len(frames)} size={frames[0].shape[1]}x{frames[0].shape[0]} device={args.device}", flush=True)

    rows = []
    for model_path in args.models:
        if not model_path.is_file():
            print(f"[skip] missing weights: {model_path}", flush=True)
            continue
        for imgsz in args.imgsz:
            row = probe(model_path, imgsz, frames, args.warmup, args.device)
            rows.append(row)
            print(f"[probe] {row['model']:14s} imgsz={imgsz:4d} p50={row['ms_p50']:7.1f}ms "
                  f"fps={row['fps']:6.1f} boxes/frame={row['boxes_per_frame']:5.2f} "
                  f"peak={row['peak_gpu_mb']}MB", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"schema": "detector-latency-probe-v1",
                    "device": args.device, "hardware": torch.cuda.get_device_name(0),
                    "frame_shape": list(frames[0].shape), "rows": rows},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PROBE DONE -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
