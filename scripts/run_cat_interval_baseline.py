#!/usr/bin/env python3
"""Run the interval-aware TSN training and held-out test on the lab server."""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/cat_interval_tsn_r50_baseline.py"
RESULT = ROOT / "results/training/cat_interval_baseline"
WORK = RESULT / "work"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(state: dict) -> None:
    path = RESULT / "run_status.json"
    temporary = path.with_suffix(".json.writing")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_command(command: list[str], log_path: Path, env: dict[str, str]) -> int:
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
    return completed.returncode


def main() -> int:
    RESULT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    for name in ("train", "val", "test"):
        if not (ROOT / f"datasets/cat_interval_baseline/{name}.jsonl").is_file():
            raise FileNotFoundError(f"Missing {name} interval index")
    if not (ROOT / "checkpoints/tsn-resnet50/tsn-resnet50_pretrained.pth").is_file():
        raise FileNotFoundError("Missing TSN pretrained checkpoint")
    state = {
        "status": "training", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": str(CONFIG), "config_sha256": sha(CONFIG), "epochs": 3,
        "batch_size": 8, "gpu": "CUDA_VISIBLE_DEVICES=0",
        "dataset_sha256": {name: sha(ROOT / f"datasets/cat_interval_baseline/{name}.jsonl")
                           for name in ("train", "val", "test")},
        "versions": {name: metadata.version(name) for name in
                     ("torch", "mmcv", "mmengine", "mmaction2", "decord")},
    }
    save(state)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["OMP_NUM_THREADS"] = "4"
    command = [sys.executable, str(ROOT / "models/mmaction2/tools/train.py"),
               str(CONFIG), "--work-dir", str(WORK)]
    train_code = run_command(command, RESULT / "train.log", env)
    state["train_exit_code"] = train_code
    if train_code:
        state["status"] = "train_failed"
        save(state)
        return train_code
    state["status"] = "testing"
    save(state)
    best = sorted(WORK.glob("best_macro_f1_epoch_*.pth"))
    checkpoints = best or sorted(WORK.glob("epoch_*.pth"))
    if not checkpoints:
        state["status"] = "checkpoint_missing"
        save(state)
        return 2
    checkpoint = checkpoints[-1]
    state["checkpoint"] = str(checkpoint)
    command = [sys.executable, str(ROOT / "models/mmaction2/tools/test.py"),
               str(CONFIG), str(checkpoint), "--work-dir", str(RESULT / "test_work")]
    test_code = run_command(command, RESULT / "test.log", env)
    state["test_exit_code"] = test_code
    state["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["status"] = "complete" if test_code == 0 else "test_failed"
    for split in ("val", "test"):
        path = RESULT / f"{split}_metrics.json"
        if path.is_file():
            report = json.loads(path.read_text(encoding="utf-8"))
            state[split + "_metrics"] = {key: report[key] for key in
                                         ("samples", "top1_acc_percent", "macro_f1_percent",
                                          "balanced_acc_percent")}
    save(state)
    return test_code


if __name__ == "__main__":
    raise SystemExit(main())
