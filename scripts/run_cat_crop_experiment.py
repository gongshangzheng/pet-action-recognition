#!/usr/bin/env python3
"""Train, select and test paired VideoMAEv2 cat-crop arms."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from collections import defaultdict
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


ARMS = ("raw", "gdino", "gdino_motion")
SPLITS = ("train", "val", "test")
RUN_ID = "gdino-crop-20261103a"
RUN_ROOT = ROOT / "results/cat_crop_classification" / RUN_ID
INDEX_ROOT = ROOT / "datasets/cat_crop_classification/gdino-v1-cat"
ASSET_ROOT = ROOT / "results/cat_crop_classification/gdino-crop-20261103a/assets/full_run"
CONFIGS = {
    "raw": ROOT / "configs/cat_crop_videomaev2_raw.py",
    "gdino": ROOT / "configs/cat_crop_videomaev2_gdino.py",
    "gdino_motion": ROOT / "configs/cat_crop_videomaev2_gdino_motion.py",
}
CLASSES = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "missing"


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def validate_common_indexes() -> dict[str, Any]:
    manifest_path = INDEX_ROOT / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("classes") != CLASSES or manifest.get("arms") != list(ARMS):
        raise ValueError("dataset manifest class or arm contract mismatch")
    if manifest.get("common_sample_set") is not True:
        raise ValueError("dataset manifest does not declare a common sample set")
    if manifest.get("training_ready") is not True:
        raise RuntimeError(
            "dataset was built from a smoke subset and is not training-ready"
        )
    source_rows = sum(len(read_jsonl(Path(manifest["source_index_root"]) / f"{split}.jsonl")) for split in SPLITS)
    if manifest.get("source_rows") != source_rows:
        raise ValueError(
            f"manifest source_rows mismatch: {manifest.get('source_rows')} != {source_rows}"
        )
    availability = json.loads((INDEX_ROOT / "availability.json").read_text(encoding="utf-8"))
    if len(availability.get("rows", [])) != source_rows:
        raise ValueError("availability rows do not match source index denominator")
    splits: dict[str, Any] = {}
    for split in SPLITS:
        arm_rows = {
            arm: read_jsonl(INDEX_ROOT / f"{arm}_{split}.jsonl") for arm in ARMS
        }
        signature = {
            arm: [
                (
                    row["sample_id"],
                    row["label"],
                    row["start_frame"],
                    row["end_frame"],
                )
                for row in rows
            ]
            for arm, rows in arm_rows.items()
        }
        if not (signature["raw"] == signature["gdino"] == signature["gdino_motion"]):
            raise ValueError(f"{split} indexes are not paired")
        if not arm_rows["raw"]:
            raise ValueError(f"{split} contains no common samples")
        for arm, rows in arm_rows.items():
            for row in rows:
                video_root = (
                    Path(manifest["source_video_root"])
                    if arm == "raw"
                    else ASSET_ROOT
                )
                video_path = (video_root / row["video"]).resolve()
                if not video_path.is_file():
                    raise FileNotFoundError(f"{arm}/{split} video missing: {video_path}")
        splits[split] = {
            "samples": len(arm_rows["raw"]),
            "hashes": {
                arm: sha256(INDEX_ROOT / f"{arm}_{split}.jsonl") for arm in ARMS
            },
        }
    return {"manifest": manifest, "splits": splits}


def config_data_root(config_path: Path) -> str:
    from mmengine.config import Config

    config = Config.fromfile(str(config_path))
    return str(config.train_dataloader.dataset.data_prefix.video)


def arm_config_options(arm: str) -> list[str]:
    result_root = RUN_ROOT / arm
    ann_file_prefix = INDEX_ROOT / f"{arm}_"
    manifest = json.loads((INDEX_ROOT / "manifest.json").read_text(encoding="utf-8"))
    arm_video_dir = (
        Path(manifest["source_video_root"])
        if arm == "raw"
        else ASSET_ROOT
    )
    return [
        f"work_dir={result_root / 'work'}",
        f"val_evaluator.out_file={result_root / 'val_metrics.json'}",
        f"test_evaluator.out_file={result_root / 'test_metrics.json'}",
        f"train_dataloader.dataset.ann_file={ann_file_prefix}train.jsonl",
        f"val_dataloader.dataset.ann_file={ann_file_prefix}val.jsonl",
        f"test_dataloader.dataset.ann_file={ann_file_prefix}test.jsonl",
        f"train_dataloader.dataset.data_prefix.video={arm_video_dir}",
        f"val_dataloader.dataset.data_prefix.video={arm_video_dir}",
        f"test_dataloader.dataset.data_prefix.video={arm_video_dir}",
        "train_dataloader.num_workers=2",
        "train_dataloader.persistent_workers=False",
        "val_dataloader.num_workers=2",
        "val_dataloader.persistent_workers=False",
        "test_dataloader.num_workers=2",
        "test_dataloader.persistent_workers=False",
    ]


def run(command: list[str], log_path: Path, env: dict[str, str]) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
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


def environment(device: str) -> dict[str, str]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = device
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["OMP_NUM_THREADS"] = "8"
    env["MKL_NUM_THREADS"] = "8"
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    return env


def find_best_checkpoint(work_dir: Path) -> Path:
    best = sorted(work_dir.glob("best_macro_f1_epoch_*.pth"))
    if best:
        return best[-1]
    epochs = sorted(work_dir.glob("epoch_*.pth"))
    if epochs:
        return epochs[-1]
    raise FileNotFoundError(f"No checkpoint in {work_dir}")


def metrics_summary(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    per_class = {row["label"]: row for row in report["per_class"]}
    return {
        "samples": report["samples"],
        "top1_acc_percent": report["top1_acc_percent"],
        "macro_f1_percent": report["macro_f1_percent"],
        "balanced_acc_percent": report["balanced_acc_percent"],
        "per_class": per_class,
        "confusion_matrix": report["confusion_matrix"],
        "predictions": report["predictions"],
    }


def evaluation_command(
    arm: str,
    checkpoint: Path,
    split: str,
    work_dir: Path,
    out_file: Path,
) -> list[str]:
    manifest = json.loads((INDEX_ROOT / "manifest.json").read_text(encoding="utf-8"))
    data_root = (
        Path(manifest["source_video_root"])
        if arm == "raw"
        else ASSET_ROOT
    )
    return [
        sys.executable,
        str(ROOT / "models/mmaction2/tools/test.py"),
        str(CONFIGS[arm]),
        str(checkpoint),
        "--work-dir",
        str(work_dir),
        "--cfg-options",
        f"test_dataloader.dataset.ann_file={INDEX_ROOT / f'{arm}_{split}.jsonl'}",
        f"test_dataloader.dataset.data_prefix.video={data_root}",
        f"test_evaluator.out_file={out_file}",
    ]


def train_arm(arm: str, device: str, epochs: int) -> dict[str, Any]:
    result = RUN_ROOT / arm
    status_path = result / "run_status.json"
    existing: dict[str, Any] = {}
    if status_path.is_file():
        existing = json.loads(status_path.read_text(encoding="utf-8"))
        if existing.get("status") == "trained":
            return existing
    result.mkdir(parents=True, exist_ok=True)
    common = validate_common_indexes()
    env = environment(device)
    work_dir = result / "work"
    checkpoint_pointer = work_dir / "last_checkpoint"
    resume_checkpoint = None
    resumable_statuses = {"train_failed", "training"}
    if existing.get("status") in resumable_statuses and checkpoint_pointer.is_file():
        checkpoint_path = Path(checkpoint_pointer.read_text(encoding="utf-8").strip())
        if checkpoint_path.is_file():
            resume_checkpoint = checkpoint_path.resolve()
    status = {
        "schema": "cat-crop-arm-v1",
        "arm": arm,
        "status": "training",
        "started_utc": utc_now(),
        "code_commit": git_head(),
        "device": device,
        "epochs": epochs,
        "seed": 0,
        "config": str(CONFIGS[arm]),
        "config_sha256": sha256(CONFIGS[arm]),
        "index_hashes": {
            split: common["splits"][split]["hashes"][arm] for split in SPLITS
        },
        "index_samples": {
            split: common["splits"][split]["samples"] for split in SPLITS
        },
        "versions": {
            name: package_version(name)
            for name in ("torch", "mmcv", "mmengine", "mmaction2", "decord")
        },
    }
    save(status_path, status)
    command = [
        sys.executable,
        str(ROOT / "models/mmaction2/tools/train.py"),
        str(CONFIGS[arm]),
        "--work-dir",
        str(work_dir),
        "--cfg-options",
        f"train_cfg.max_epochs={epochs}",
        f"param_scheduler.1.end={epochs}",
        *arm_config_options(arm),
    ]
    if resume_checkpoint is not None:
        command.extend(["--resume", str(resume_checkpoint)])
        status["resume_from"] = str(resume_checkpoint)
        status["resumed_after_failed_attempt"] = existing.get("started_utc")
    status["train_exit_code"] = run(command, result / "train.log", env)
    if status["train_exit_code"]:
        status["status"] = "train_failed"
        save(status_path, status)
        return status
    checkpoint = find_best_checkpoint(work_dir)
    status.update(
        checkpoint=str(checkpoint),
        checkpoint_sha256=sha256(checkpoint),
        status="validating",
    )
    save(status_path, status)
    best_val = result / "best_val_metrics.json"
    command = evaluation_command(
        arm, checkpoint, "val", result / "best_val_work", best_val
    )
    status["best_val_exit_code"] = run(command, result / "best_val.log", env)
    if status["best_val_exit_code"] or not best_val.is_file():
        status["status"] = "validation_failed"
        save(status_path, status)
        return status
    status["best_val_metrics"] = metrics_summary(best_val)
    status["best_val_metrics_sha256"] = sha256(best_val)
    status["status"] = "trained"
    status["completed_training_utc"] = utc_now()
    save(status_path, status)
    return status


def selection_score(state: dict[str, Any]) -> tuple[float, ...]:
    validation = state["best_val_metrics"]
    per_class = validation["per_class"]
    simplicity = -ARMS.index(state["arm"])
    return (
        float(validation["macro_f1_percent"]),
        float(per_class["toileting"]["recall_percent"]),
        float(per_class["abnormal"]["recall_percent"]),
        float(per_class["grooming"]["recall_percent"]),
        float(validation["balanced_acc_percent"]),
        float(validation["top1_acc_percent"]),
        float(simplicity),
    )


def select_arms(arms: list[str] | None = None) -> dict[str, Any]:
    selection_path = RUN_ROOT / "selection.json"
    if selection_path.is_file():
        return json.loads(selection_path.read_text(encoding="utf-8"))
    states = {}
    for arm in arms or ARMS:
        path = RUN_ROOT / arm / "run_status.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") != "trained":
            raise RuntimeError(f"{arm} is not trained: {state.get('status')}")
        if list((RUN_ROOT / arm).glob("test*")):
            raise RuntimeError(f"{arm} has test artifacts before selection")
        states[arm] = state
    ranked = sorted(states.values(), key=selection_score, reverse=True)
    selection = {
        "schema": "cat-crop-selection-v1",
        "selected_utc": utc_now(),
        "rule": (
            "validation macro_f1 then toileting, abnormal and grooming recall, "
            "balanced accuracy, top1, then simpler input representation"
        ),
        "winner": ranked[0]["arm"],
        "arms": {
            state["arm"]: {
                "checkpoint": state["checkpoint"],
                "checkpoint_sha256": state["checkpoint_sha256"],
                "best_val_metrics": state["best_val_metrics"],
            }
            for state in ranked
        },
        "test_exposure": (
            "historical seven-class test split was exposed before this change; "
            "results are benchmark reevaluation only"
        ),
    }
    save(selection_path, selection)
    return selection


def test_arms(device: str, arms: list[str] | None = None) -> dict[str, Any]:
    selection = select_arms(arms)
    env = environment(device)
    for arm in arms or ARMS:
        result = RUN_ROOT / arm
        status_path = result / "run_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        test_path = result / "test_metrics.json"
        if status.get("status") == "complete" and test_path.is_file():
            continue
        status["status"] = "testing"
        save(status_path, status)
        command = evaluation_command(
            arm,
            Path(selection["arms"][arm]["checkpoint"]),
            "test",
            result / "test_work",
            test_path,
        )
        status["test_exit_code"] = run(command, result / "test.log", env)
        if status["test_exit_code"] or not test_path.is_file():
            status["status"] = "test_failed"
            save(status_path, status)
            raise RuntimeError(f"{arm} test failed")
        status["test_metrics"] = metrics_summary(test_path)
        status["test_metrics_sha256"] = sha256(test_path)
        status["status"] = "complete"
        status["completed_utc"] = utc_now()
        save(status_path, status)
    report = build_report(selection)
    return report


def prediction_map(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in metrics["predictions"]}


def macro_f1(truth: np.ndarray, predicted: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(
        f1_score(truth, predicted, labels=range(len(CLASSES)), average="macro")
    )


def grouped_delta_interval(
    groups: list[list[tuple[int, int, int]]],
    seed: int = 0,
    draws: int = 1000,
) -> list[float]:
    if not groups:
        return [0.0, 0.0]
    rng = random.Random(seed)
    deltas = []
    for _ in range(draws):
        sampled_groups = [rng.choice(groups) for _ in groups]
        truth: list[int] = []
        left: list[int] = []
        right: list[int] = []
        for group in sampled_groups:
            for label, prediction_a, prediction_b in group:
                truth.append(label)
                left.append(prediction_a)
                right.append(prediction_b)
        truth_array = np.asarray(truth)
        deltas.append(
            macro_f1(truth_array, np.asarray(right))
            - macro_f1(truth_array, np.asarray(left))
        )
    return [
        100 * float(np.percentile(deltas, 2.5)),
        100 * float(np.percentile(deltas, 97.5)),
    ]


def comparison(
    left_arm: str, right_arm: str, states: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    left = prediction_map(states[left_arm]["test_metrics"])
    right = prediction_map(states[right_arm]["test_metrics"])
    if set(left) != set(right):
        raise ValueError(f"{left_arm} and {right_arm} test samples differ")
    by_video: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    changed = {
        "wrong_to_right": 0,
        "right_to_wrong": 0,
        "both_right": 0,
        "both_wrong": 0,
    }
    for row in read_jsonl(INDEX_ROOT / "raw_test.jsonl"):
        sample_id = row["sample_id"]
        truth = int(row["label"])
        prediction_left = int(left[sample_id]["predicted"])
        prediction_right = int(right[sample_id]["predicted"])
        correct_left = prediction_left == truth
        correct_right = prediction_right == truth
        key = (
            "wrong_to_right"
            if not correct_left and correct_right
            else "right_to_wrong"
            if correct_left and not correct_right
            else "both_right"
            if correct_left
            else "both_wrong"
        )
        changed[key] += 1
        by_video[row["video"]].append((truth, prediction_left, prediction_right))
    accuracy_delta = (
        states[right_arm]["test_metrics"]["top1_acc_percent"]
        - states[left_arm]["test_metrics"]["top1_acc_percent"]
    )
    return {
        "left": left_arm,
        "right": right_arm,
        "accuracy_delta_percentage_points": accuracy_delta,
        "paired": changed,
        "grouped_macro_f1_delta_ci95_percentage_points": grouped_delta_interval(
            list(by_video.values())
        ),
        "group_unit": "source_video",
    }


def original_denominator(source_index_root: Path) -> dict[str, Any]:
    source_test = read_jsonl(source_index_root / "test.jsonl")
    common_test = read_jsonl(INDEX_ROOT / "raw_test.jsonl")
    common_ids = {row["sample_id"] for row in common_test}
    missing = [row for row in source_test if row["sample_id"] not in common_ids]
    return {
        "original_intervals": len(source_test),
        "eligible_intervals": len(common_test),
        "unavailable_intervals": len(missing),
        "availability_percent": 100 * len(common_test) / max(1, len(source_test)),
    }


def build_report(selection: dict[str, Any]) -> dict[str, Any]:
    dataset_manifest = json.loads(
        (INDEX_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    states = {
        arm: json.loads(
            (RUN_ROOT / arm / "run_status.json").read_text(encoding="utf-8")
        )
        for arm in ARMS
    }
    denominator = original_denominator(Path(dataset_manifest["source_index_root"]))
    for arm in ARMS:
        metrics = states[arm]["test_metrics"]
        correct = sum(
            row["label"] == row["predicted"] for row in metrics["predictions"]
        )
        states[arm]["pipeline_test"] = {
            **denominator,
            "correct_available_intervals": correct,
            "conditional_top1_percent": metrics["top1_acc_percent"],
            "top1_over_original_percent": 100
            * correct
            / denominator["original_intervals"],
        }
    summary = {
        "schema": "cat-crop-summary-v1",
        "created_utc": utc_now(),
        "run_id": RUN_ID,
        "selection": selection,
        "test_exposure": selection["test_exposure"],
        "availability": denominator,
        "availability_by_split": dataset_manifest["availability"],
        "arms": {
            arm: {
                "status": states[arm]["status"],
                "best_val": states[arm]["best_val_metrics"],
                "test": states[arm]["test_metrics"],
                "pipeline_test": states[arm]["pipeline_test"],
                "checkpoint": states[arm]["checkpoint"],
                "checkpoint_sha256": states[arm]["checkpoint_sha256"],
            }
            for arm in ARMS
        },
        "paired_comparisons": {
            "crop_vs_raw": comparison("raw", "gdino", states),
            "motion_vs_crop": comparison("gdino", "gdino_motion", states),
        },
    }
    save(RUN_ROOT / "summary.json", summary)
    lines = [
        f"# Cat crop experiment {RUN_ID}",
        "",
        "区间级结果；历史测试集已暴露，不能称为全新独立测试或事件级验收。",
        "",
        "| arm | val top1 | val macro-F1 | test top1 | test macro-F1 | test balanced acc |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        data = summary["arms"][arm]
        lines.append(
            f"| {arm} | {data['best_val']['top1_acc_percent']:.2f}% | "
            f"{data['best_val']['macro_f1_percent']:.2f}% | "
            f"{data['test']['top1_acc_percent']:.2f}% | "
            f"{data['test']['macro_f1_percent']:.2f}% | "
            f"{data['test']['balanced_acc_percent']:.2f}% |"
        )
    lines.extend(
        [
            "",
            f"共同可用测试区间：{denominator['eligible_intervals']}/"
            f"{denominator['original_intervals']}（{denominator['availability_percent']:.2f}%）。",
            "",
            f"验证集选择胜出臂：`{selection['winner']}`。",
            "",
            "完整逐样本预测、混淆矩阵和配对变化见 `summary.json` 及各臂指标文件。",
        ]
    )
    (RUN_ROOT / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def preflight_arm(arm: str, runtime_device: str) -> dict[str, Any]:
    import torch
    from mmengine.config import Config
    from mmengine.runner import Runner
    from mmaction.registry import MODELS

    config = Config.fromfile(str(CONFIGS[arm]))
    manifest = json.loads((INDEX_ROOT / "manifest.json").read_text(encoding="utf-8"))
    video_root = (
        Path(manifest["source_video_root"])
        if arm == "raw"
        else ASSET_ROOT
    )
    config.train_dataloader.dataset.ann_file = str(INDEX_ROOT / f"{arm}_train.jsonl")
    config.train_dataloader.dataset.data_prefix.video = str(video_root)
    model = MODELS.build(config.model)
    model.init_weights()
    loader_config = copy.deepcopy(config.train_dataloader)
    loader_config.update(num_workers=2, persistent_workers=False)
    loader = Runner.build_dataloader(loader_config, seed=0)
    batch = next(iter(loader))
    model = model.to(runtime_device).train()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(runtime_device)
    data = model.data_preprocessor(batch, training=True)
    scaler = torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available())
    with torch.autocast("cuda", dtype=torch.float16, enabled=torch.cuda.is_available()):
        losses = model(**data, mode="loss")
    loss = sum(value for key, value in losses.items() if "loss" in key)
    if not torch.isfinite(loss):
        raise ValueError(f"{arm}: non-finite loss")
    scaler.scale(loss).backward()
    result = {
        "passed": True,
        "input_shape": list(data["inputs"].shape),
        "loss": float(loss.detach().cpu()),
        "peak_memory_mib": (
            torch.cuda.max_memory_allocated(runtime_device) / 1024**2
            if torch.cuda.is_available()
            else 0
        ),
    }
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return result


def preflight(device: str) -> dict[str, Any]:
    common = validate_common_indexes()
    os.environ["CUDA_VISIBLE_DEVICES"] = device
    import torch
    from mmaction.utils import register_all_modules

    import petlib.datasets.cat_intervals  # noqa: F401

    register_all_modules(init_default_scope=True)
    runtime_device = "cuda:0" if torch.cuda.is_available() else "cpu"
    report: dict[str, Any] = {
        "code_commit": git_head(),
        "physical_device": device,
        "runtime_device": runtime_device,
        "arms": {},
    }
    for arm in ARMS:
        report["arms"][arm] = preflight_arm(arm, runtime_device)
    report["indexes"] = common["splits"]
    save(RUN_ROOT / "preflight.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=("preflight", "train", "select", "test", "report")
    )
    parser.add_argument("--device", default="1")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    args = parser.parse_args()
    if args.stage == "preflight":
        print(json.dumps(preflight(args.device), ensure_ascii=False, indent=2))
        return 0
    if args.stage == "train":
        for arm in args.arms:
            state = train_arm(arm, args.device, args.epochs)
            print(json.dumps({"arm": arm, "status": state["status"]}), flush=True)
            if state["status"] != "trained":
                return 1
        return 0
    if args.stage == "select":
        print(json.dumps(select_arms(args.arms), ensure_ascii=False, indent=2))
        return 0
    if args.stage == "test":
        print(json.dumps(test_arms(args.device, args.arms), ensure_ascii=False, indent=2))
        return 0
    selection = json.loads((RUN_ROOT / "selection.json").read_text(encoding="utf-8"))
    print(json.dumps(build_report(selection), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
