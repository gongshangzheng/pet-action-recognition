#!/usr/bin/env python3
"""Train TSN/TSM R50 on the seven-class v1 index and select on validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]
MODELS = {
    "tsn_r50": {
        "config": ROOT / "configs/cat_action_tsn_r50_v1.py",
        "checkpoint": ROOT / "checkpoints/tsn-resnet50/tsn-resnet50_pretrained.pth",
        "result": ROOT / "results/training/cat_action_v1/tsn_r50",
    },
    "tsm_r50": {
        "config": ROOT / "configs/cat_action_tsm_r50_v1.py",
        "checkpoint": ROOT / "checkpoints/tsm-resnet50/tsm-resnet50_pretrained.pth",
        "result": ROOT / "results/training/cat_action_v1/tsm_r50",
    },
}
INDEX_ROOT = ROOT / "datasets/cat_action_v1"
DATA_ROOT = ROOT / "datasets/cat_raw"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save(state: dict, result: Path) -> None:
    path = result / "run_status.json"
    temporary = path.with_suffix(".json.writing")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "missing"


def load_summary(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    per_class = {row["label"]: row for row in report["per_class"]}
    return {
        "samples": report["samples"],
        "top1_acc_percent": report["top1_acc_percent"],
        "macro_f1_percent": report["macro_f1_percent"],
        "balanced_acc_percent": report["balanced_acc_percent"],
        "per_class": per_class,
        "abnormal": per_class["abnormal"],
        "toileting": per_class["toileting"],
    }


def run(command: list[str], log_path: Path, env: dict[str, str]) -> int:
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    return completed.returncode


def command_for_model(name: str, info: dict, checkpoint: Path, work_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "models/mmaction2/tools/test.py"),
        str(info["config"]),
        str(checkpoint),
        "--work-dir",
        str(work_dir),
    ]


def find_best_checkpoint(work_dir: Path) -> Path:
    best = sorted(work_dir.glob("best_macro_f1_epoch_*.pth"))
    if best:
        return best[-1]
    epochs = sorted(work_dir.glob("epoch_*.pth"))
    if epochs:
        return epochs[-1]
    raise FileNotFoundError(f"No checkpoint found in {work_dir}")


def train_model(
    name: str,
    info: dict,
    env: dict[str, str],
    epochs: int,
    dry_run: bool,
) -> dict:
    result = info["result"]
    result.mkdir(parents=True, exist_ok=True)
    work = result / "work"
    work.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": "cat-action-training-v1",
        "model": name,
        "status": "starting",
        "purpose": "v1 model selection on validation only",
        "started_utc": utc_now(),
        "config": str(info["config"]),
        "config_sha256": sha256(info["config"]),
        "index_sha256": {
            split: sha256(INDEX_ROOT / f"{split}.jsonl")
            for split in ("train", "val", "test")
        },
        "checkpoint_source": str(info["checkpoint"]),
        "checkpoint_source_sha256": sha256(info["checkpoint"]),
        "epochs": epochs,
        "batch_size": 16,
        "gpu": env["CUDA_VISIBLE_DEVICES"],
        "versions": {
            package: version(package)
            for package in ("torch", "mmcv", "mmengine", "mmaction2", "decord")
        },
    }
    save(state, result)
    train_cmd = [
        sys.executable,
        str(ROOT / "models/mmaction2/tools/train.py"),
        str(info["config"]),
        "--work-dir",
        str(work),
        "--cfg-options",
        f"train_cfg.max_epochs={epochs}",
        f"param_scheduler.1.end={epochs}",
    ]
    if dry_run:
        print(f"[dry-run] {name} train: {' '.join(train_cmd)}")
        state["status"] = "dry_run"
        save(state, result)
        return state
    state["status"] = "training"
    save(state, result)
    code = run(train_cmd, result / "train.log", env)
    state["train_exit_code"] = code
    if code:
        state["status"] = "train_failed"
        save(state, result)
        return state

    checkpoint = find_best_checkpoint(work)
    state["checkpoint"] = str(checkpoint)
    state["checkpoint_sha256"] = sha256(checkpoint)
    best_val_path = result / "best_val_metrics.json"
    val_cmd = command_for_model(name, info, checkpoint, result / "best_val_work")
    val_cmd += [
        "--cfg-options",
        f"test_dataloader.dataset.ann_file={INDEX_ROOT / 'val.jsonl'}",
        f"test_evaluator.out_file={best_val_path}",
    ]
    state["status"] = "validating_best_checkpoint"
    save(state, result)
    code = run(val_cmd, result / "best_val.log", env)
    state["best_val_exit_code"] = code
    if code or not best_val_path.is_file():
        state["status"] = "validation_failed"
        save(state, result)
        return state
    summary = load_summary(best_val_path)
    state["best_val_metrics"] = summary
    state["abnormal_recall_percent"] = summary["abnormal"]["recall_percent"]
    state["abnormal_support"] = summary["abnormal"]["support"]
    state["toileting_recall_percent"] = summary["toileting"]["recall_percent"]
    state["toileting_support"] = summary["toileting"]["support"]
    state["status"] = "trained"
    state["completed_train_utc"] = utc_now()
    save(state, result)
    print(
        json.dumps(
            {
                "model": name,
                "best_checkpoint": str(checkpoint),
                "val_macro_f1_percent": summary["macro_f1_percent"],
                "abnormal_recall_percent": summary["abnormal"]["recall_percent"],
                "abnormal_support": summary["abnormal"]["support"],
                "toileting_recall_percent": summary["toileting"]["recall_percent"],
                "toileting_support": summary["toileting"]["support"],
            },
            ensure_ascii=False,
        )
    )
    return state


def select(candidates: dict[str, dict], result: Path) -> dict:
    def score(state: dict) -> tuple:
        val = state["best_val_metrics"]
        return (
            val["macro_f1_percent"],
            val["toileting"]["recall_percent"],
            val["abnormal"]["recall_percent"],
            val["per_class"]["grooming"]["recall_percent"],
            val["per_class"]["drinking"]["recall_percent"],
            val["balanced_acc_percent"],
            val["top1_acc_percent"],
        )

    ranked = sorted(
        candidates.items(), key=lambda item: score(item[1]), reverse=True
    )
    winner = ranked[0][0]
    selection = {
        "schema": "cat-action-training-v1",
        "rule": (
            "validation macro_f1_percent primary; then toileting, abnormal, "
            "grooming and drinking recall, balanced accuracy and top1; "
            "test is not used"
        ),
        "candidates": {
            name: {
                "best_checkpoint": state["checkpoint"],
                "best_val_metrics": state["best_val_metrics"],
                "abnormal_recall_percent": state["abnormal_recall_percent"],
                "abnormal_support": state["abnormal_support"],
                "toileting_recall_percent": state["toileting_recall_percent"],
                "toileting_support": state["toileting_support"],
            }
            for name, state in candidates.items()
        },
        "winner": winner,
        "selected_utc": utc_now(),
    }
    path = result / "selection.json"
    path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"winner": winner, "selection": str(path)}, ensure_ascii=False))
    return selection


def test_model(
    name: str,
    info: dict,
    state: dict,
    env: dict[str, str],
    dry_run: bool,
) -> dict:
    result = info["result"]
    checkpoint = Path(state["checkpoint"])
    test_path = result / "test_metrics.json"
    test_cmd = command_for_model(name, info, checkpoint, result / "test_work")
    if dry_run:
        print(f"[dry-run] {name} test: {' '.join(test_cmd)}")
        state["status"] = "dry_run"
        save(state, result)
        return state
    state["status"] = "testing"
    save(state, result)
    code = run(test_cmd, result / "test.log", env)
    state["test_exit_code"] = code
    if code or not test_path.is_file():
        state["status"] = "test_failed"
        save(state, result)
        return state
    summary = load_summary(test_path)
    state["test_metrics"] = summary
    state["status"] = "complete"
    state["completed_utc"] = utc_now()
    save(state, result)
    print(
        json.dumps(
            {
                "model": name,
                "test_macro_f1_percent": summary["macro_f1_percent"],
                "test_abnormal_recall_percent": summary["abnormal"]["recall_percent"],
                "test_abnormal_support": summary["abnormal"]["support"],
                "test_toileting_recall_percent": summary["toileting"]["recall_percent"],
                "test_toileting_support": summary["toileting"]["support"],
            },
            ensure_ascii=False,
        )
    )
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=sorted(MODELS),
        default=sorted(MODELS),
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--device", default="1")
    parser.add_argument("--skip-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if sorted(args.models) != sorted(MODELS):
        raise SystemExit("Model selection requires both tsn_r50 and tsm_r50")
    for split in ("train", "val", "test"):
        if not (INDEX_ROOT / f"{split}.jsonl").is_file():
            raise FileNotFoundError(INDEX_ROOT / f"{split}.jsonl")
    if not (DATA_ROOT / "videos").is_dir():
        raise FileNotFoundError(DATA_ROOT / "videos")
    for info in MODELS.values():
        if not info["config"].is_file():
            raise FileNotFoundError(info["config"])
        if not info["checkpoint"].is_file():
            raise FileNotFoundError(info["checkpoint"])

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.device
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["OMP_NUM_THREADS"] = "4"
    result_root = ROOT / "results/training/cat_action_v1"
    result_root.mkdir(parents=True, exist_ok=True)

    candidates: dict[str, dict] = {}
    for name in sorted(MODELS):
        print(f"=== training {name} ===")
        candidates[name] = train_model(
            name, MODELS[name], env, args.epochs, args.dry_run
        )
        if candidates[name]["status"] not in ("trained", "dry_run"):
            return 1
    if args.dry_run:
        return 0
    selection = select(candidates, result_root)
    if args.skip_test:
        print(json.dumps({"winner": selection["winner"], "tests": "skipped"}))
        return 0
    for name in sorted(MODELS):
        print(f"=== testing {name} ===")
        candidates[name] = test_model(
            name, MODELS[name], candidates[name], env, args.dry_run
        )
        if candidates[name]["status"] != "complete":
            return 1
    selection["tests"] = {
        name: {
            "test_metrics": state["test_metrics"],
            "checkpoint": state["checkpoint"],
        }
        for name, state in candidates.items()
    }
    (result_root / "selection.json").write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"winner": selection["winner"], "status": "complete"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
