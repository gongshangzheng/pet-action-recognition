#!/usr/bin/env python3
"""Preflight v1 configs, model heads, datasets and decoded interval samples."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mmengine.config import Config
from mmaction.registry import DATASETS, MODELS
from mmaction.utils import register_all_modules

import petlib.datasets.cat_intervals  # noqa: F401 - registry side effect


def main() -> None:
    register_all_modules(init_default_scope=True)
    result = {}
    for config_name in ("cat_action_tsn_r50_v1.py", "cat_action_tsm_r50_v1.py"):
        cfg = Config.fromfile(str(ROOT / "configs" / config_name))
        if len(cfg.classes) != 7:
            raise AssertionError(f"{config_name}: expected 7 classes")
        weights = cfg.model.cls_head.loss_cls.class_weight
        if len(weights) != 7:
            raise AssertionError(f"{config_name}: expected 7 class weights")
        model = MODELS.build(cfg.model)
        model.init_weights()
        if model.cls_head.fc_cls.out_features != 7:
            raise AssertionError(f"{config_name}: unexpected class head")
        entry = {
            "classes": list(cfg.classes),
            "class_weight": list(weights),
            "model_built": True,
            "splits": {},
        }
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
                raise AssertionError(f"{config_name} {split}: frame outside interval")
            decoded = dataset[0]
            label = int(decoded["data_samples"].gt_label.item())
            if not 0 <= label < 7:
                raise AssertionError(f"{config_name} {split}: invalid label {label}")
            entry["splits"][split] = {
                "samples": len(dataset),
                "first_video": info["filename"],
                "interval": [info["interval_start"], info["interval_end"]],
                "sampled_frames": indices,
                "input_shape": list(decoded["inputs"].shape),
                "label": label,
            }
        result[config_name] = entry
    output = ROOT / "results/training/cat_action_v1/preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        name: {
            "classes": entry["classes"],
            "splits": {split: info["samples"] for split, info in entry["splits"].items()},
        }
        for name, entry in result.items()
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
