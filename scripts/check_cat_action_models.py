#!/usr/bin/env python3
"""Preflight the cat action v1 reference models before any training starts.

Per model: build it and apply the pretrained weights the way the runner will,
prove the backbone tensors equal the checkpoint, check that sampled frames lie
inside the labeled interval (including the shortest intervals), and run one
real forward/backward batch under fp16 autocast to measure peak GPU memory.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from mmengine.config import Config
from mmengine.runner import Runner
from mmengine.runner.checkpoint import _load_checkpoint, load_checkpoint
from mmaction.registry import DATASETS, MODELS
from mmaction.utils import register_all_modules

import petlib.datasets.cat_intervals  # noqa: F401 - registry side effect

CONFIGS = {
    "videomaev2_b": "cat_action_videomaev2_b_v1.py",
    "uniformerv2_b": "cat_action_uniformerv2_b_v1.py",
    "x3d_s": "cat_action_x3d_s_v1.py",
    "slowfast_r50": "cat_action_slowfast_r50_v1.py",
}
MIN_BACKBONE_MATCH = 0.98
PEAK_MEMORY_LIMIT_GIB = 21.0
SHORTEST_PER_SPLIT = 5
SAMPLE_DRAWS = 3


def checkpoint_path(cfg: Config) -> Path:
    if cfg.get("load_from"):
        return ROOT / cfg.load_from
    init_cfg = cfg.model.backbone.get("init_cfg")
    if init_cfg and init_cfg.get("checkpoint"):
        return ROOT / init_cfg["checkpoint"]
    raise ValueError("config has no pretrained checkpoint")


def check_weights(cfg: Config, model: torch.nn.Module) -> dict:
    model.init_weights()
    if cfg.get("load_from"):
        load_checkpoint(model, str(ROOT / cfg.load_from), map_location="cpu",
                        strict=False)
    path = checkpoint_path(cfg)
    checkpoint = _load_checkpoint(str(path), map_location="cpu")
    source = checkpoint.get("state_dict", checkpoint)
    state = model.state_dict()
    matched = total = unmatched = 0
    missing, shape_mismatch = [], []
    buffers = {name for name, _ in model.named_buffers()}
    for key, value in state.items():
        if not key.startswith("backbone.") or key.endswith("num_batches_tracked"):
            continue
        if key in buffers and key not in source:
            continue  # fixed buffers (e.g. VideoMAE sinusoid pos_embed) are not in the checkpoint
        total += value.numel()
        if key not in source:
            missing.append(key)
            unmatched += value.numel()
        elif source[key].shape != value.shape:
            shape_mismatch.append(key)
            unmatched += value.numel()
        elif torch.equal(source[key].cpu(), value.cpu()):
            matched += value.numel()
        else:
            unmatched += value.numel()
    fraction = matched / total
    return {
        "checkpoint": str(path),
        "backbone_numel": total,
        "backbone_matched_fraction": fraction,
        "missing_keys": len(missing),
        "missing_examples": missing[:5],
        "shape_mismatch_keys": len(shape_mismatch),
        "passed": fraction >= MIN_BACKBONE_MATCH,
    }


def check_intervals(cfg: Config) -> dict:
    result = {}
    for split in ("train", "val", "test"):
        dataset = DATASETS.build(cfg[f"{split}_dataloader"]["dataset"])
        order = sorted(range(len(dataset)), key=lambda i: (
            dataset.get_data_info(i)["interval_end"]
            - dataset.get_data_info(i)["interval_start"]))
        indices = [0, 1, 2] + order[:SHORTEST_PER_SPLIT]
        for index in indices:
            info = dataset.get_data_info(index)
            start, end = info["interval_start"] - 1, info["interval_end"] - 1
            for _ in range(SAMPLE_DRAWS):
                partial = dict(info)
                for transform in dataset.pipeline.transforms[:3]:
                    partial = transform(partial)
                frames = partial["frame_inds"].tolist()
                if min(frames) < start or max(frames) > end:
                    raise AssertionError(
                        f"{split}[{index}]: frames {min(frames)}..{max(frames)} "
                        f"outside interval {start}..{end}")
        decoded = dataset[order[0]]
        label = int(decoded["data_samples"].gt_label.item())
        if not 0 <= label < 7:
            raise AssertionError(f"{split}: invalid label {label}")
        result[split] = {
            "samples": len(dataset),
            "checked_indices": len(indices),
            "shortest_interval_frames": info["interval_end"] - info["interval_start"] + 1,
            "input_shape": list(decoded["inputs"].shape),
        }
    return result


def check_batch(cfg: Config, model: torch.nn.Module, device: str) -> dict:
    loader_cfg = copy.deepcopy(cfg.train_dataloader)
    loader_cfg.update(num_workers=4, persistent_workers=False)
    loader = Runner.build_dataloader(loader_cfg, seed=0)
    batch = next(iter(loader))
    model = model.to(device).train()
    torch.cuda.reset_peak_memory_stats(device)
    data = model.data_preprocessor(batch, training=True)
    scaler = torch.cuda.amp.GradScaler()
    with torch.autocast("cuda", dtype=torch.float16):
        losses = model(**data, mode="loss")
    loss = sum(value for key, value in losses.items() if "loss" in key)
    if not torch.isfinite(loss):
        raise AssertionError(f"non-finite loss {loss.item()}")
    scaler.scale(loss).backward()
    peak = torch.cuda.max_memory_allocated(device) / 1024 ** 3
    return {
        "batch_size": cfg.train_dataloader.batch_size,
        "loss": float(loss.item()),
        "peak_memory_gib": peak,
        "passed": peak <= PEAK_MEMORY_LIMIT_GIB,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=sorted(CONFIGS),
                        default=sorted(CONFIGS))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--skip-gpu", action="store_true")
    args = parser.parse_args()
    register_all_modules(init_default_scope=True)
    report = {}
    for name in args.models:
        cfg = Config.fromfile(str(ROOT / "configs" / CONFIGS[name]))
        entry = {"config": CONFIGS[name]}
        try:
            model = MODELS.build(cfg.model)
            entry["weights"] = check_weights(cfg, model)
            entry["intervals"] = check_intervals(cfg)
            if not args.skip_gpu:
                entry["gpu_batch"] = check_batch(cfg, model, args.device)
            entry["passed"] = entry["weights"]["passed"] and entry.get(
                "gpu_batch", {"passed": True})["passed"]
        except Exception as exc:  # report every model's failure, not just the first
            entry["passed"] = False
            entry["error"] = f"{type(exc).__name__}: {exc}"
        report[name] = entry
        print(json.dumps({name: {k: v for k, v in entry.items()
                                 if k in ("passed", "error")}}, ensure_ascii=False))
        torch.cuda.empty_cache()
    out = ROOT / "results/training/cat_action_v1/model_zoo_preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({name: entry["passed"] for name, entry in report.items()}))
    return 0 if all(entry["passed"] for entry in report.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
