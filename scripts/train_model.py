#!/usr/bin/env python3
"""pet-action-recognition 训练入口 — mmaction2 vendor 包装。

用法（由 server/routers/training.py POST /run 触发）：
  python3 scripts/train_model.py \
    --model-id tsn-resnet50 --dataset-id quadruped_action \
    --run-id train-1234567890 \
    --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
    --epochs 100 --lr 1e-4 --batch-size 16 --device cuda \
    [--resume] [--extra-args "--amp --seed 42"]

流程：
  1. 校验四足数据集目录/标注文件（不存在则记录 error 到 metrics.json 后退出）。
  2. 用 mmaction2 的 tools/train.py 启动训练，work_dir=results/training/work_dirs/<run_id>/。
  3. 解析 vis_data/scalars.json 生成 loss_series。
  4. 把最新 epoch_*.pth 软链/复制到 results/training/checkpoints/<run_id>.pth。
  5. 追加/更新 run 到 results/training/metrics.json（status: running -> completed/error）。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import (
    TRAINING_DIR,
    TRAINING_METRICS_JSON,
    CHECKPOINTS_DIR,
    TRAINING_LOGS_DIR,
    TRAINING_WORK_DIR,
    MMACTION2_DIR,
    QUADRUPED_DATASET_NAME,
    QUADRUPED_DATASET_DIR,
    QUADRUPED_CLASSES_FILE,
)

TRAIN_PY = os.path.join(MMACTION2_DIR, "tools", "train.py")
VIDEO_EXTS = (".mp4", ".avi", ".mov", ".mkv", ".webm")


def log(run_id: str, msg: str) -> None:
    os.makedirs(TRAINING_LOGS_DIR, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(os.path.join(TRAINING_LOGS_DIR, f"{run_id}.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ensure_dirs() -> None:
    for d in (TRAINING_DIR, CHECKPOINTS_DIR, TRAINING_LOGS_DIR, TRAINING_WORK_DIR):
        os.makedirs(d, exist_ok=True)


def _cpu_patch_dir() -> str:
    """macOS MPS 会选 float64 不支持的设备，通过 sitecustomize 强制 CPU。"""
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


def load_metrics() -> dict:
    if not os.path.isfile(TRAINING_METRICS_JSON):
        return {"generated_at": None, "runs": []}
    try:
        with open(TRAINING_METRICS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "runs" in data:
            return data
        return {"generated_at": None, "runs": data if isinstance(data, list) else []}
    except (json.JSONDecodeError, OSError):
        return {"generated_at": None, "runs": []}


def save_metrics(data: dict) -> None:
    os.makedirs(os.path.dirname(TRAINING_METRICS_JSON), exist_ok=True)
    tmp = TRAINING_METRICS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TRAINING_METRICS_JSON)


def upsert_run(run: dict) -> None:
    data = load_metrics()
    runs = data.setdefault("runs", [])
    for i, r in enumerate(runs):
        if r.get("id") == run.get("id"):
            runs[i] = {**r, **run}
            break
    else:
        runs.append(run)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_metrics(data)


def num_classes_for(dataset_id: str) -> int | None:
    """从 classes.txt / class_map.json 推断类别数；无则返回 None。"""
    if os.path.isfile(QUADRUPED_CLASSES_FILE):
        with open(QUADRUPED_CLASSES_FILE, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if lines:
            return len(lines)
    cm = os.path.join(QUADRUPED_DATASET_DIR, "class_map.json")
    if os.path.isfile(cm):
        try:
            with open(cm, "r", encoding="utf-8") as f:
                return len(json.load(f))
        except Exception:
            pass
    return None


def resolve_dataset_paths(dataset_id: str):
    """返回训练/验证所需的 ann_file 与 data_root；若数据集未构建则返回空字符串。"""
    if dataset_id == QUADRUPED_DATASET_NAME:
        root = Path(QUADRUPED_DATASET_DIR)
    else:
        root = REPO / "datasets" / dataset_id
    if not root.is_dir():
        return "", "", "", ""
    name = root.name
    ann_train = root / f"{name}_train_list.txt"
    ann_val = root / f"{name}_val_list.txt"
    videos_train = root / "videos_train"
    videos_val = root / "videos_val"
    return (
        str(ann_train) if ann_train.is_file() else "",
        str(videos_train) if videos_train.is_dir() else "",
        str(ann_val) if ann_val.is_file() else "",
        str(videos_val) if videos_val.is_dir() else "",
    )


def build_train_command(args, ann_train: str, videos_train: str, ann_val: str, videos_val: str) -> list[str]:
    cfg_path = args.mmaction2_config
    if not os.path.isabs(cfg_path):
        cfg_path = os.path.join(MMACTION2_DIR, cfg_path)
    cmd = [sys.executable, TRAIN_PY, cfg_path, "--work-dir", args.work_dir, "--launcher", "none"]
    if args.seed is not None:
        cmd += ["--seed", str(args.seed)]
    if args.resume:
        cmd += ["--resume", args.resume if args.resume != "auto" else "auto"]

    cfg_options = [
        f"train_cfg.max_epochs={args.epochs}",
        f"optim_wrapper.optimizer.lr={args.lr}",
        f"train_dataloader.batch_size={args.batch_size}",
        f"val_dataloader.batch_size={max(1, args.batch_size // 2)}",
    ]
    n_cls = args.num_classes if args.num_classes is not None else num_classes_for(args.dataset_id)
    if n_cls is not None:
        cfg_options.append(f"model.cls_head.num_classes={n_cls}")
    if ann_train:
        cfg_options.append(f"train_dataloader.dataset.ann_file={ann_train}")
    if videos_train:
        cfg_options.append(f"train_dataloader.dataset.data_prefix.video={videos_train}")
    if ann_val:
        cfg_options.append(f"val_dataloader.dataset.ann_file={ann_val}")
    if videos_val:
        cfg_options.append(f"val_dataloader.dataset.data_prefix.video={videos_val}")

    if cfg_options:
        cmd += ["--cfg-options"] + cfg_options
    if args.extra_args:
        cmd += args.extra_args.split()
    return cmd


def parse_scalars(work_dir: str) -> list[dict]:
    """解析 mmengine 的 vis_data/scalars.json，返回 {epoch, loss, top1_acc, top5_acc, lr} 列表。"""
    path = os.path.join(work_dir, "vis_data", "scalars.json")
    if not os.path.isfile(path):
        # 新版 mmengine 把时间戳子目录也包含进 work_dir，递归查找
        for root, _dirs, files in os.walk(work_dir):
            if "scalars.json" in files:
                path = os.path.join(root, "scalars.json")
                break
        else:
            return []
    series: list[dict] = []
    seen_epochs: set[int] = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                epoch = obj.get("epoch")
                if epoch is None:
                    continue
                # 每个 epoch 只保留最后一条（汇总）
                rec = next((r for r in series if r["epoch"] == epoch), None)
                if rec is None:
                    rec = {"epoch": epoch}
                    series.append(rec)
                if "loss" in obj:
                    rec["loss"] = float(obj["loss"])
                if "top1_acc" in obj:
                    rec["top1_acc"] = float(obj["top1_acc"])
                if "top5_acc" in obj:
                    rec["top5_acc"] = float(obj["top5_acc"])
                if "acc/top1" in obj:
                    rec.setdefault("top1_acc", float(obj["acc/top1"]))
                if "acc/top5" in obj:
                    rec.setdefault("top5_acc", float(obj["acc/top5"]))
                if "lr" in obj:
                    rec["lr"] = float(obj["lr"])
        series.sort(key=lambda x: x["epoch"])
    except Exception:
        pass
    return series


def find_latest_checkpoint(work_dir: str) -> str | None:
    """返回 work_dir 中最新 epoch_*.pth 的绝对路径。"""
    if not os.path.isdir(work_dir):
        return None
    cks = [
        os.path.join(work_dir, fn)
        for fn in os.listdir(work_dir)
        if fn.startswith("epoch_") and fn.endswith(".pth")
    ]
    if not cks:
        return None
    # epoch_1.pth ... epoch_100.pth；按文件 mtime/数字排序
    def epoch_of(p: str) -> int:
        try:
            return int(os.path.basename(p)[6:-4])
        except ValueError:
            return 0
    return max(cks, key=epoch_of)


def link_checkpoint(src: str, run_id: str) -> str | None:
    if not src or not os.path.isfile(src):
        return None
    dst = os.path.join(CHECKPOINTS_DIR, f"{run_id}.pth")
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.symlink(os.path.relpath(src, CHECKPOINTS_DIR), dst)
    except OSError:
        shutil.copy2(src, dst)
    return f"checkpoints/{run_id}.pth"


def main() -> int:
    parser = argparse.ArgumentParser(description="mmaction2 training wrapper for pet-action-recognition")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mmaction2-config", required=True, help="mmaction2 config path (relative to MMACTION2_DIR or absolute)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--resume", default=None, help="resume from checkpoint path or 'auto'")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--extra-args", default="", help="extra CLI args passed to tools/train.py")
    args = parser.parse_args()

    ensure_dirs()
    work_dir = args.work_dir or os.path.join(TRAINING_WORK_DIR, args.run_id)
    os.makedirs(work_dir, exist_ok=True)
    args.work_dir = work_dir

    run = {
        "id": args.run_id,
        "model": args.model_id,
        "dataset": args.dataset_id,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epochs": args.epochs,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "device": args.device,
        "checkpoint_path": None,
        "metrics": {},
        "loss_series": [],
    }
    upsert_run(run)
    log(args.run_id, f"[start] model={args.model_id} dataset={args.dataset_id} work_dir={work_dir}")

    ann_train, videos_train, ann_val, videos_val = resolve_dataset_paths(args.dataset_id)
    if not ann_train or not os.path.isfile(ann_train):
        if args.dataset_id == QUADRUPED_DATASET_NAME:
            expected = os.path.join(QUADRUPED_DATASET_DIR, f"{QUADRUPED_DATASET_NAME}_train_list.txt")
        else:
            expected = os.path.join(str(REPO), "datasets", args.dataset_id, f"{args.dataset_id}_train_list.txt")
        err = f"训练标注文件不存在：{expected}。请先按 using-mmaction2 skill 准备数据集。"
        log(args.run_id, f"[error] {err}")
        run["status"] = "error"
        run["metrics"]["error"] = err
        upsert_run(run)
        return 1

    cmd = build_train_command(args, ann_train, videos_train, ann_val, videos_val)
    log(args.run_id, f"[cmd] {' '.join(cmd)}")

    env = os.environ.copy()
    # PyTorch >=2.6 默认 weights_only=True，mmengine 保存的 checkpoint 含 HistoryBuffer 会失败
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    # 让 mmaction2 可 import（未 pip install -e 时）
    ppath = [str(MMACTION2_DIR), str(REPO)]
    if args.device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""
        # macOS MPS 不支持 float64，强制让 mmengine 选择 CPU
        ppath.insert(0, _cpu_patch_dir())
    if env.get("PYTHONPATH"):
        ppath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(ppath)

    log_file = os.path.join(TRAINING_LOGS_DIR, f"{args.run_id}.log")
    ret = 1
    try:
        with open(log_file, "a", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                cmd,
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(REPO),
            )
            log(args.run_id, f"[pid] {proc.pid}")
            ret = proc.wait()
    except Exception as e:
        log(args.run_id, f"[error] 启动训练子进程失败：{e}")
        run["status"] = "error"
        run["metrics"]["error"] = str(e)
        upsert_run(run)
        return 1

    # 解析产物
    run["loss_series"] = parse_scalars(work_dir)
    latest = find_latest_checkpoint(work_dir)
    cp_rel = link_checkpoint(latest, args.run_id) if latest else None
    run["checkpoint_path"] = cp_rel
    if cp_rel:
        run["metrics"]["latest_epoch"] = int(os.path.basename(latest)[6:-4])

    if run["loss_series"]:
        last = run["loss_series"][-1]
        run["metrics"].update({k: last[k] for k in ("loss", "top1_acc", "top5_acc", "lr") if k in last})
        run["final_loss"] = last.get("loss")
        run["best_metric"] = last.get("top1_acc")

    if ret == 0:
        run["status"] = "completed"
        log(args.run_id, "[done] 训练完成")
    else:
        run["status"] = "error"
        run["metrics"]["returncode"] = ret
        log(args.run_id, f"[error] 训练进程退出码 {ret}")

    upsert_run(run)
    return ret


if __name__ == "__main__":
    sys.exit(main())
