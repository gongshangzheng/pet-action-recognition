#!/usr/bin/env python3
"""mmaction2 测试/评估包装。

用法：
  python3 scripts/run_test.py \
    --run-id test-1234567890 \
    --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
    --checkpoint results/training/work_dirs/train-xxx/epoch_100.pth \
    --dataset-id quadruped_action \
    --split test

流程：
  1. 根据 split 定位 ann_file / data_root。
  2. 调用 models/mmaction2/tools/test.py，覆盖 test_dataloader。
  3. 解析 stdout 中的 acc/top1、acc/top5，写入 results/training/test_results.json。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import (
    MMACTION2_DIR,
    QUADRUPED_DATASET_NAME,
    QUADRUPED_DATASET_DIR,
    TRAINING_DIR,
    TRAINING_WORK_DIR,
    CHECKPOINTS_DIR,
    resolve_mmaction2_config,
)

TEST_PY = os.path.join(MMACTION2_DIR, "tools", "test.py")
RESULTS_JSON = os.path.join(TRAINING_DIR, "test_results.json")


def ensure_dirs() -> None:
    os.makedirs(TRAINING_DIR, exist_ok=True)


def _cpu_patch_dir() -> str:
    """macOS MPS 不支持 float64，通过 sitecustomize 强制 CPU。"""
    d = os.path.join(TRAINING_WORK_DIR, ".cpu_sitecustomize")
    os.makedirs(d, exist_ok=True)
    sf = os.path.join(d, "sitecustomize.py")
    if not os.path.isfile(sf):
        with open(sf, "w", encoding="utf-8") as f:
            f.write(
                "import torch\n"
                "if hasattr(torch.backends, 'mps'):\n"
                "    torch.backends.mps.is_available = lambda: False\n"
            )
    return d


def load_results() -> dict:
    if not os.path.isfile(RESULTS_JSON):
        return {"generated_at": None, "results": []}
    try:
        with open(RESULTS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "results" in data:
            return data
        return {"generated_at": None, "results": data if isinstance(data, list) else []}
    except (json.JSONDecodeError, OSError):
        return {"generated_at": None, "results": []}


def save_results(data: dict) -> None:
    tmp = RESULTS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, RESULTS_JSON)


def resolve_test_paths(dataset_id: str, split: str):
    if dataset_id == QUADRUPED_DATASET_NAME:
        root = Path(QUADRUPED_DATASET_DIR)
    else:
        root = REPO / "datasets" / dataset_id
    if not root.is_dir():
        return None, None
    ann = root / f"{root.name}_{split}_list.txt"
    videos = root / f"videos_{split}"
    return (str(ann) if ann.is_file() else None), (str(videos) if videos.is_dir() else None)


def parse_metrics(stdout: str) -> dict:
    metrics = {}
    for line in stdout.splitlines():
        m = re.search(r"acc/top1\s*[:=]?\s*([0-9.]+)", line)
        if m:
            metrics["top1_acc"] = float(m.group(1))
        m = re.search(r"acc/top5\s*[:=]?\s*([0-9.]+)", line)
        if m:
            metrics["top5_acc"] = float(m.group(1))
        # mean class accuracy（per-class 平均，抗类别不均衡；mmengine AccMetric 输出 acc/mean1）
        m = re.search(r"acc/mean1\s*[:=]?\s*([0-9.]+)", line)
        if m:
            metrics["mean1_acc"] = float(m.group(1))
        m = re.search(r"acc/mean5\s*[:=]?\s*([0-9.]+)", line)
        if m:
            metrics["mean5_acc"] = float(m.group(1))
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="mmaction2 test wrapper")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mmaction2-config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset-id", default="quadruped_action")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--ann-file", default=None, help="覆盖 ann_file 路径（K400 等非默认命名数据集用）")
    parser.add_argument("--data-root", default=None, help="覆盖 data_prefix.video 路径")
    parser.add_argument("--extra-args", default="")
    args = parser.parse_args()

    ensure_dirs()
    cfg_path = args.mmaction2_config
    if not os.path.isabs(cfg_path):
        cfg_path = resolve_mmaction2_config(cfg_path)

    checkpoint = args.checkpoint
    if not os.path.isabs(checkpoint):
        checkpoint = os.path.join(CHECKPOINTS_DIR, os.path.basename(checkpoint))

    work_dir = args.work_dir or os.path.join(TRAINING_WORK_DIR, f"test_{args.run_id}")
    os.makedirs(work_dir, exist_ok=True)

    ann = args.ann_file or None
    videos = args.data_root or None
    if not ann or not videos:
        ann2, videos2 = resolve_test_paths(args.dataset_id, args.split)
        ann = ann or ann2
        videos = videos or videos2
    if not ann:
        err = f"测试标注不存在：{args.dataset_id}/{args.split}"
        print(f"[error] {err}")
        result = {
            "id": args.run_id,
            "model": os.path.basename(args.mmaction2_config),
            "dataset": args.dataset_id,
            "split": args.split,
            "checkpoint": checkpoint,
            "metrics": {},
            "stdout_tail": err,
            "status": "error",
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data = load_results()
        data["results"] = [r for r in data.get("results", []) if r.get("id") != args.run_id]
        data["results"].append(result)
        data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_results(data)
        return 1

    cmd = [
        sys.executable,
        TEST_PY,
        cfg_path,
        checkpoint,
        "--work-dir",
        work_dir,
        "--launcher",
        "none",
    ]
    cfg_options = [
        f"test_dataloader.dataset.ann_file={ann}",
    ]
    if videos:
        cfg_options.append(f"test_dataloader.dataset.data_prefix.video={videos}")
    if args.num_classes is not None:
        cfg_options.append(f"model.cls_head.num_classes={args.num_classes}")
        # AccMetric topk: avoid meaningless top5 on small datasets
        ks = tuple(k for k in (1, 5) if k <= args.num_classes)
        cfg_options.append(f"test_evaluator.metric_options.top_k_accuracy.topk={ks}")
    if cfg_options:
        cmd += ["--cfg-options"] + cfg_options
    if args.extra_args:
        cmd += args.extra_args.split()

    print(f"[cmd] {' '.join(cmd)}")
    env = os.environ.copy()
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    ppath = [str(MMACTION2_DIR), str(REPO)]
    if args.device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""
        ppath.insert(0, _cpu_patch_dir())
    if env.get("PYTHONPATH"):
        ppath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(ppath)

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(REPO),
    )
    print(proc.stdout)

    metrics = parse_metrics(proc.stdout)

    # 速度 + 大小维度：test 成功后跑 benchmark_speed（latency/fps/rtf/gpu_mem/param/ckpt_size）
    if proc.returncode == 0 and ann and videos:
        try:
            from scripts.benchmark_speed import benchmark
            dev = "cuda:0" if args.device == "cuda" else "cpu"
            b = benchmark(args.mmaction2_config, checkpoint, ann, videos, num_videos=5, device=dev)
            if "error" not in b:
                metrics["speed"] = {k: b[k] for k in
                                    ("latency_ms", "fps", "rtf", "gpu_mem_mb", "param_count_m", "ckpt_size_mb")
                                    if k in b}
                print(f"[bench] latency={b.get('latency_ms')}ms fps={b.get('fps')} rtf={b.get('rtf')} "
                      f"gpu={b.get('gpu_mem_mb')}MB params={b.get('param_count_m')}M ckpt={b.get('ckpt_size_mb')}MB")
        except Exception as e:
            print(f"[bench] 失败: {e}")

    result = {
        "id": args.run_id,
        "model": os.path.basename(args.mmaction2_config),
        "dataset": args.dataset_id,
        "split": args.split,
        "checkpoint": checkpoint,
        "metrics": metrics,
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-30:]),
        "status": "completed" if proc.returncode == 0 else "error",
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data = load_results()
    data["results"] = [r for r in data.get("results", []) if r.get("id") != args.run_id]
    data["results"].append(result)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_results(data)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
