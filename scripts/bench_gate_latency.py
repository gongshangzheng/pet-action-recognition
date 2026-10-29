#!/usr/bin/env python3
"""门控模型速度与体积基准：单帧延迟（p50/p90）、吞吐、参数量、显存。

为什么单帧而不是只测吞吐：门控是**逐帧**判定，实际调用是「一次一帧」，
批量吞吐会掩盖真实延迟；两者都测，才是可用的数字。

用法（GPU/CPU 都能跑；共享机请用 remote_run 包起来）：
  python3 scripts/bench_gate_latency.py --checkpoint results/gate/runs/<run>/best.pt \
      --arch mobilenet_v3_small --sizes 256 320 448 640 --device cuda:0 --fp16
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path


def build_model(arch: str):
    import torch
    from torchvision import models

    if arch == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 2)
    elif arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 2)
    elif arch == "resnet18":
        model = models.resnet18(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, 2)
    else:
        raise ValueError(f"未知 arch: {arch}")
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", default="mobilenet_v3_small")
    parser.add_argument("--sizes", type=int, nargs="+", default=[256, 320, 448, 640])
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--batch", type=int, default=32, help="吞吐测量用的批量")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    import torch

    torch.set_num_threads(4)
    device = args.device
    model = build_model(args.arch).to(device).eval()
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    if args.fp16 and "cuda" in device:
        model = model.half()
    params = sum(p.numel() for p in model.parameters())
    print(f"[bench] {args.arch} params={params/1e6:.2f}M device={device} fp16={args.fp16}")

    rows = []
    for size in args.sizes:
        height = size
        width = int(round(size * 16 / 9))
        tensor = torch.randn(1, 3, height, width, device=device)
        if args.fp16 and "cuda" in device:
            tensor = tensor.half()
        with torch.no_grad():
            for _ in range(args.warmup):
                model(tensor)
            if "cuda" in device:
                torch.cuda.synchronize()
            latencies = []
            for _ in range(args.runs):
                start = time.perf_counter()
                model(tensor)
                if "cuda" in device:
                    torch.cuda.synchronize()
                latencies.append((time.perf_counter() - start) * 1000)
        # 吞吐
        batch = torch.randn(args.batch, 3, height, width, device=device)
        if args.fp16 and "cuda" in device:
            batch = batch.half()
        with torch.no_grad():
            for _ in range(3):
                model(batch)
            if "cuda" in device:
                torch.cuda.synchronize()
            start = time.perf_counter()
            for _ in range(5):
                model(batch)
            if "cuda" in device:
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
        throughput = (5 * args.batch) / elapsed

        row = {
            "size": f"{width}x{height}",
            "short_side": size,
            "p50_ms": round(statistics.median(latencies), 2),
            "p90_ms": round(sorted(latencies)[int(0.9 * len(latencies)) - 1], 2),
            "fps_single": round(1000 / statistics.median(latencies), 1),
            "throughput_fps": round(throughput, 1),
        }
        rows.append(row)
        print(f"[bench] 输入 {row['size']:>9s}  单帧 p50 {row['p50_ms']:6.2f} ms / p90 {row['p90_ms']:6.2f} ms "
              f"({row['fps_single']:5.1f} FPS)  批量吞吐 {row['throughput_fps']:7.1f} FPS")

    if "cuda" in device:
        print(f"[bench] 显存峰值 {torch.cuda.max_memory_allocated() / 1024**2:.0f} MiB")

    report = {"arch": args.arch, "params_m": round(params / 1e6, 3), "device": device,
              "fp16": args.fp16, "rows": rows}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[bench] 报告 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
