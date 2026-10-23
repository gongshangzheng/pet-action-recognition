#!/usr/bin/env python3
"""Check interval datasets, frame sampling and one decoded sample per split."""
from __future__ import annotations

import json
from pathlib import Path

from mmengine.config import Config
from mmaction.registry import DATASETS
from mmaction.utils import register_all_modules

import petlib.datasets.cat_intervals  # noqa: F401 - registry side effect


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    register_all_modules(init_default_scope=True)
    cfg = Config.fromfile(str(ROOT / "configs/cat_interval_tsn_r50_baseline.py"))
    result = {}
    for split in ("train", "val", "test"):
        dataset = DATASETS.build(cfg[f"{split}_dataloader"]["dataset"])
        info = dataset.get_data_info(0)
        partial = dict(info)
        for transform in dataset.pipeline.transforms[:3]:
            partial = transform(partial)
        indices = partial["frame_inds"].tolist()
        start = info["interval_start"] - 1
        end = info["interval_end"] - 1
        if min(indices) < start or max(indices) > end:
            raise AssertionError(f"{split}: sampled frame outside labeled interval")
        decoded = dataset[0]
        result[split] = {
            "samples": len(dataset), "first_video": info["filename"],
            "interval": [info["interval_start"], info["interval_end"]],
            "sampled_frames": indices, "input_shape": list(decoded["inputs"].shape),
            "label": int(decoded["data_samples"].gt_label.item()),
        }
    output = ROOT / "results/training/cat_interval_baseline/preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
