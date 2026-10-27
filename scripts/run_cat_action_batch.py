#!/usr/bin/env python3
"""Train, rank and test the cat action v1 reference models.

Stages: ``train`` (sequential queue on one GPU; a failure does not stop the
queue), ``rank`` (validation metrics only; writes the ranking once, before any
new model's test split is evaluated) and ``test`` (needs the ranking file).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_cat_action_v1 import (  # noqa: E402
    CLASSES, INDEX_ROOT, ROOT, command_for_model, find_best_checkpoint,
    load_summary, run, save, sha256, test_model, utc_now, version,
)

RESULT_ROOT = ROOT / "results/training/cat_action_v1"
RANKING = RESULT_ROOT / "model_zoo_ranking.json"
SUMMARY = RESULT_ROOT / "model_zoo_summary.json"
REFERENCE = {
    "videomaev2_b": ("cat_action_videomaev2_b_v1.py",
                     "checkpoints/videomaev2-base/videomaev2-base_pretrained.pth"),
    "uniformerv2_b": ("cat_action_uniformerv2_b_v1.py",
                      "checkpoints/uniformerv2-base/uniformerv2-base_pretrained.pth"),
    "x3d_s": ("cat_action_x3d_s_v1.py",
              "checkpoints/x3d-xs/x3d-xs_pretrained.pth"),
    "slowfast_r50": ("cat_action_slowfast_r50_v1.py",
                     "checkpoints/slowfast-resnet50/slowfast-resnet50_pretrained.pth"),
}
BASELINES = ("tsn_r50", "tsm_r50")


def info_for(name: str) -> dict:
    config, weights = REFERENCE[name]
    return {"config": ROOT / "configs" / config, "checkpoint": ROOT / weights,
            "result": RESULT_ROOT / name}


def load_state(name: str) -> dict:
    return json.loads((RESULT_ROOT / name / "run_status.json").read_text(encoding="utf-8"))


def score(state: dict) -> tuple:
    val = state["best_val_metrics"]
    per_class = val["per_class"]
    return (val["macro_f1_percent"], per_class["toileting"]["recall_percent"],
            per_class["abnormal"]["recall_percent"],
            per_class["grooming"]["recall_percent"],
            per_class["drinking"]["recall_percent"],
            val["balanced_acc_percent"], val["top1_acc_percent"])


def train_one(name: str, env: dict[str, str], epochs: int) -> dict:
    from mmengine.config import Config

    info = info_for(name)
    result = info["result"]
    (result / "work").mkdir(parents=True, exist_ok=True)
    cfg = Config.fromfile(str(info["config"]))
    accumulation = cfg.optim_wrapper.get("accumulative_counts", 1)
    state = {
        "schema": "cat-action-model-zoo-v1", "model": name, "status": "training",
        "purpose": "reference model; ranked on validation only",
        "started_utc": utc_now(),
        "config": str(info["config"]), "config_sha256": sha256(info["config"]),
        "index_sha256": {split: sha256(INDEX_ROOT / f"{split}.jsonl")
                         for split in ("train", "val", "test")},
        "checkpoint_source": str(info["checkpoint"]),
        "checkpoint_source_sha256": sha256(info["checkpoint"]),
        "epochs": epochs,
        "batch_size": cfg.train_dataloader.batch_size,
        "accumulative_counts": accumulation,
        "effective_batch_size": cfg.train_dataloader.batch_size * accumulation,
        "amp": cfg.optim_wrapper.type == "AmpOptimWrapper",
        "gpu": env["CUDA_VISIBLE_DEVICES"],
        "versions": {package: version(package) for package in
                     ("torch", "mmcv", "mmengine", "mmaction2", "decord")},
    }
    save(state, result)
    command = [sys.executable, str(ROOT / "models/mmaction2/tools/train.py"),
               str(info["config"]), "--work-dir", str(result / "work"),
               "--cfg-options", f"train_cfg.max_epochs={epochs}",
               f"param_scheduler.1.end={epochs}"]
    state["train_exit_code"] = run(command, result / "train.log", env)
    if state["train_exit_code"]:
        state["status"] = "train_failed"
        save(state, result)
        return state
    checkpoint = find_best_checkpoint(result / "work")
    state["checkpoint"] = str(checkpoint)
    state["checkpoint_sha256"] = sha256(checkpoint)
    best_val = result / "best_val_metrics.json"
    command = command_for_model(name, info, checkpoint, result / "best_val_work") + [
        "--cfg-options", f"test_dataloader.dataset.ann_file={INDEX_ROOT / 'val.jsonl'}",
        f"test_evaluator.out_file={best_val}"]
    state["status"] = "validating_best_checkpoint"
    save(state, result)
    state["best_val_exit_code"] = run(command, result / "best_val.log", env)
    if state["best_val_exit_code"] or not best_val.is_file():
        state["status"] = "validation_failed"
        save(state, result)
        return state
    summary = load_summary(best_val)
    state.update(best_val_metrics=summary, status="trained",
                 abnormal_recall_percent=summary["abnormal"]["recall_percent"],
                 abnormal_support=summary["abnormal"]["support"],
                 toileting_recall_percent=summary["toileting"]["recall_percent"],
                 toileting_support=summary["toileting"]["support"],
                 completed_train_utc=utc_now())
    save(state, result)
    return state


def stage_train(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.device
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["OMP_NUM_THREADS"] = "4"
    failed = []
    for name in args.models:
        print(f"=== training {name} on GPU {args.device} ===", flush=True)
        state = train_one(name, env, args.epochs)
        print(json.dumps({"model": name, "status": state["status"]}), flush=True)
        if state["status"] != "trained":
            failed.append(name)
    return 1 if failed else 0


def stage_rank(args: argparse.Namespace) -> int:
    if RANKING.exists():
        raise SystemExit(f"{RANKING} already exists; the ranking is frozen")
    states = {name: load_state(name) for name in (*BASELINES, *REFERENCE)}
    for name, state in states.items():
        if "best_val_metrics" not in state:
            raise SystemExit(f"{name} has no validation metrics (status {state['status']})")
    early = [name for name in REFERENCE if "test_metrics" in states[name]]
    if early:
        raise SystemExit(f"test already evaluated for {early}; refusing to rank")
    ordered = sorted(states, key=lambda name: score(states[name]), reverse=True)
    ranking = {
        "schema": "cat-action-model-zoo-v1", "frozen_utc": utc_now(),
        "rule": "validation macro_f1; then toileting, abnormal, grooming, drinking "
                "recall, balanced accuracy, top1. Test metrics are not used.",
        "caveat": "val support: abnormal 18, toileting 4, grooming 19; "
                  "small macro-F1 gaps are not reliable",
        "ranking": [{"rank": i + 1, "model": name,
                     "val_top1": states[name]["best_val_metrics"]["top1_acc_percent"],
                     "val_macro_f1": states[name]["best_val_metrics"]["macro_f1_percent"],
                     "val_balanced_acc": states[name]["best_val_metrics"]["balanced_acc_percent"],
                     "val_recall": {c: states[name]["best_val_metrics"]["per_class"][c]["recall_percent"]
                                    for c in CLASSES},
                     "checkpoint": states[name]["checkpoint"],
                     "checkpoint_sha256": states[name]["checkpoint_sha256"]}
                    for i, name in enumerate(ordered)],
    }
    RANKING.write_text(json.dumps(ranking, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([(row["rank"], row["model"], round(row["val_macro_f1"], 2))
                      for row in ranking["ranking"]]))
    return 0


def stage_test(args: argparse.Namespace) -> int:
    if not RANKING.is_file():
        raise SystemExit("run the rank stage first; the ranking must be frozen before testing")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.device
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    for name in args.models:
        state = load_state(name)
        if state["status"] != "trained":
            raise SystemExit(f"{name} is {state['status']}, not trained")
        state = test_model(name, info_for(name), state, env, dry_run=False)
        if state["status"] != "complete":
            return 1
    summary = {}
    for name in (*BASELINES, *REFERENCE):
        state = load_state(name)
        summary[name] = {"val": state.get("best_val_metrics"), "test": state.get("test_metrics"),
                         "checkpoint": state.get("checkpoint")}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    train = sub.add_parser("train")
    train.add_argument("--models", nargs="+", choices=sorted(REFERENCE), required=True)
    train.add_argument("--device", required=True)
    train.add_argument("--epochs", type=int, default=20)
    sub.add_parser("rank")
    test = sub.add_parser("test")
    test.add_argument("--models", nargs="+", choices=sorted(REFERENCE), default=sorted(REFERENCE))
    test.add_argument("--device", required=True)
    args = parser.parse_args()
    return {"train": stage_train, "rank": stage_rank, "test": stage_test}[args.stage](args)


if __name__ == "__main__":
    raise SystemExit(main())
