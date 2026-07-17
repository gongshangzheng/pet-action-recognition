#!/usr/bin/env python3
"""pet-action-recognition 训练入口 — mmaction2 vendor 包装。

用法（由 server/routers/training.py POST /run 触发）：
  python3 scripts/train_model.py \
    --model-id tsn-resnet50 --dataset-id quadruped_action \
    --run-id train-1234567890 \
    --mmaction2-config configs/recognition/tsn/... \
    --epochs 100 --lr 1e-4 --batch-size 16 --device cuda

四种训练模式（互斥，都不选则使用 config 默认值）：
  --resume <path>         断点续训，复用 run_id，恢复 epoch/optimizer/scheduler
  --load-from <path|id>   加载我们 checkpoint 的权重，epoch=0 从头训练
  --pretrained <url|path> 加载 backbone 预训练权重（mmaction2 模型仓库 URL 或本地路径），finetune
  --from-scratch          随机初始化，禁用 config 中的任何预训练权重

流程：
  1. 校验四足数据集目录/标注文件。
  2. 用 mmaction2 的 tools/train.py 启动训练。
  3. 解析 vis_data/scalars.json 生成 loss_series。
  4. 把 latest + best checkpoint 软链到 results/training/checkpoints/<model_id>/，附带 JSON 元数据。
  5. 追加/更新 run 到 results/training/metrics.json。
"""
from __future__ import annotations

import argparse
import json
import os
import re
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
    if getattr(args, "load_from", None):
        cfg_options.append(f"load_from={args.load_from}")
    if getattr(args, "pretrained", None):
        cfg_options.append(f"load_from={args.pretrained}")
    if getattr(args, "from_scratch", False):
        cfg_options.append("model.backbone.init_cfg=None")

    if cfg_options:
        cmd += ["--cfg-options"] + cfg_options
    if args.extra_args:
        cmd += args.extra_args.split()
    return cmd


def parse_scalars(work_dir: str) -> list[dict]:
    path = os.path.join(work_dir, "vis_data", "scalars.json")
    if not os.path.isfile(path):
        for root, _dirs, files in os.walk(work_dir):
            if "scalars.json" in files:
                path = os.path.join(root, "scalars.json")
                break
        else:
            return []
    series: list[dict] = []
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
    if not os.path.isdir(work_dir):
        return None
    cks = [
        os.path.join(work_dir, fn)
        for fn in os.listdir(work_dir)
        if fn.startswith("epoch_") and fn.endswith(".pth")
    ]
    if not cks:
        return None

    def epoch_of(p: str) -> int:
        try:
            return int(os.path.basename(p)[6:-4])
        except ValueError:
            return 0
    return max(cks, key=epoch_of)


def find_best_checkpoint(work_dir: str) -> str | None:
    if not os.path.isdir(work_dir):
        return None
    pattern = re.compile(r"^best_.*_epoch_(\d+)\.pth$")
    best_path = None
    best_epoch = -1
    for fn in os.listdir(work_dir):
        m = pattern.match(fn)
        if m:
            epoch = int(m.group(1))
            if epoch > best_epoch:
                best_epoch = epoch
                best_path = os.path.join(work_dir, fn)
    return best_path


def _ckpt_dir(model_id: str) -> str:
    d = os.path.join(CHECKPOINTS_DIR, model_id)
    os.makedirs(d, exist_ok=True)
    return d


def link_checkpoint(src: str, model_id: str, run_id: str, suffix: str) -> str | None:
    if not src or not os.path.isfile(src):
        return None
    dst_dir = _ckpt_dir(model_id)
    dst = os.path.join(dst_dir, f"{run_id}_{suffix}.pth")
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.symlink(os.path.relpath(src, dst_dir), dst)
    except OSError:
        shutil.copy2(src, dst)
    return f"checkpoints/{model_id}/{run_id}_{suffix}.pth"


def write_checkpoint_meta(
    model_id: str,
    run_id: str,
    ckpt_type: str,
    epoch: int,
    total_epochs: int,
    metrics: dict,
    source_file: str,
    dataset_id: str = "",
) -> str:
    dst_dir = _ckpt_dir(model_id)
    meta = {
        "run_id": run_id,
        "model_id": model_id,
        "dataset": dataset_id,
        "type": ckpt_type,
        "epoch": epoch,
        "total_epochs": total_epochs,
        "metrics": metrics,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint_path": f"checkpoints/{model_id}/{run_id}_{ckpt_type}.pth",
        "source_file": source_file,
    }
    meta_path = os.path.join(dst_dir, f"{run_id}_{ckpt_type}.json")
    tmp = meta_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, meta_path)
    return meta_path


def resolve_checkpoint_path(path_or_run_id: str, model_id: str) -> str | None:
    if os.path.isfile(path_or_run_id):
        return path_or_run_id
    ckpt_file = os.path.join(CHECKPOINTS_DIR, model_id, f"{path_or_run_id}_latest.pth")
    if os.path.isfile(ckpt_file):
        return os.path.realpath(ckpt_file)
    for fn in os.listdir(CHECKPOINTS_DIR) if os.path.isdir(CHECKPOINTS_DIR) else []:
        candidate = os.path.join(CHECKPOINTS_DIR, fn, f"{path_or_run_id}_latest.pth")
        if os.path.isfile(candidate):
            return os.path.realpath(candidate)
    return None


def _read_old_best_top1(model_id: str, run_id: str) -> float | None:
    meta_path = os.path.join(CHECKPOINTS_DIR, model_id, f"{run_id}_best.json")
    if not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("metrics", {}).get("top1_acc")
    except (json.JSONDecodeError, OSError):
        return None


def _metrics_for_epoch(series: list[dict], epoch: int) -> dict:
    for rec in series:
        if rec.get("epoch") == epoch:
            return {k: rec[k] for k in ("loss", "top1_acc", "top5_acc", "lr") if k in rec}
    return {}


def _epoch_of_file(path: str) -> int:
    fn = os.path.basename(path)
    m = re.search(r"epoch_(\d+)\.pth$", fn)
    return int(m.group(1)) if m else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="mmaction2 training wrapper for pet-action-recognition")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mmaction2-config", required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--resume", default=None, help="resume from checkpoint path or 'auto'")
    parser.add_argument("--load-from", default=None, help="load our checkpoint weights (path or run_id); starts from epoch 0")
    parser.add_argument("--pretrained", default=None, help="backbone pretrained weights URL or local path (e.g. mmaction2 model zoo)")
    parser.add_argument("--from-scratch", action="store_true", help="train from random init, disable any pretrained weights in config")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--extra-args", default="")
    args = parser.parse_args()

    modes = [
        ("resume", args.resume),
        ("load_from", args.load_from),
        ("pretrained", args.pretrained),
        ("from_scratch", args.from_scratch or None),
    ]
    active = [name for name, val in modes if val]
    if len(active) > 1:
        parser.error(f"训练模式互斥，只能选一个：{', '.join(active)}")

    ensure_dirs()

    is_resume = bool(args.resume)
    work_dir = args.work_dir or os.path.join(TRAINING_WORK_DIR, args.run_id)
    os.makedirs(work_dir, exist_ok=True)
    args.work_dir = work_dir

    if args.load_from:
        resolved = resolve_checkpoint_path(args.load_from, args.model_id)
        if resolved:
            args.load_from = resolved
        else:
            log(args.run_id, f"[warn] load_from 未找到有效 checkpoint：{args.load_from}")

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
        "best_checkpoint_path": None,
        "metrics": {},
        "loss_series": [],
    }
    if is_resume:
        run["resumed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if args.load_from:
        run["loaded_from"] = args.load_from
    if args.pretrained:
        run["pretrained"] = args.pretrained
    if args.from_scratch:
        run["from_scratch"] = True
    upsert_run(run)
    log(args.run_id, f"[start] model={args.model_id} dataset={args.dataset_id} work_dir={work_dir}"
        + (" [resume]" if is_resume else "")
        + (f" [load_from={args.load_from}]" if args.load_from else "")
        + (f" [pretrained={args.pretrained}]" if args.pretrained else "")
        + (" [from_scratch]" if args.from_scratch else ""))

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
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    ppath = [str(MMACTION2_DIR), str(REPO)]
    if args.device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""
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
    series = parse_scalars(work_dir)
    run["loss_series"] = series

    # --- latest checkpoint ---
    latest = find_latest_checkpoint(work_dir)
    latest_rel = None
    if latest:
        latest_rel = link_checkpoint(latest, args.model_id, args.run_id, "latest")
        ep = _epoch_of_file(latest)
        m = _metrics_for_epoch(series, ep)
        write_checkpoint_meta(
            args.model_id, args.run_id, "latest",
            epoch=ep, total_epochs=args.epochs, metrics=m,
            source_file=os.path.basename(latest),
            dataset_id=args.dataset_id,
        )
        run["checkpoint_path"] = latest_rel
        run["metrics"]["latest_epoch"] = ep
        run["metrics"].update(m)

    # --- best checkpoint ---
    best = find_best_checkpoint(work_dir)
    if best:
        best_ep = _epoch_of_file(best)
        best_metrics = _metrics_for_epoch(series, best_ep)
        should_save = True
        if is_resume:
            old_top1 = _read_old_best_top1(args.model_id, args.run_id)
            new_top1 = best_metrics.get("top1_acc")
            if old_top1 is not None and new_top1 is not None and new_top1 <= old_top1:
                should_save = False
                log(args.run_id, f"[best] 新 best top1={new_top1} 未超过旧 best top1={old_top1}，保留旧 best")

        if should_save:
            link_checkpoint(best, args.model_id, args.run_id, "best")
            write_checkpoint_meta(
                args.model_id, args.run_id, "best",
                epoch=best_ep, total_epochs=args.epochs, metrics=best_metrics,
                source_file=os.path.basename(best),
                dataset_id=args.dataset_id,
            )
            run["best_checkpoint_path"] = f"checkpoints/{args.model_id}/{args.run_id}_best.pth"
            run["metrics"]["best_epoch"] = best_ep
            if best_metrics.get("top1_acc") is not None:
                run["best_metric"] = best_metrics["top1_acc"]
    elif not is_resume and latest:
        # 没有 val 阶段产出的 best，用 latest 作为 best
        latest_ep = _epoch_of_file(latest)
        latest_metrics = _metrics_for_epoch(series, latest_ep)
        link_checkpoint(latest, args.model_id, args.run_id, "best")
        write_checkpoint_meta(
            args.model_id, args.run_id, "best",
            epoch=latest_ep, total_epochs=args.epochs, metrics=latest_metrics,
            source_file=os.path.basename(latest),
            dataset_id=args.dataset_id,
        )
        run["best_checkpoint_path"] = f"checkpoints/{args.model_id}/{args.run_id}_best.pth"

    if series:
        last = series[-1]
        run["final_loss"] = last.get("loss")
        if run.get("best_metric") is None:
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
