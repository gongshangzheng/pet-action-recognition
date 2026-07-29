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
    resolve_mmaction2_config,
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
    # 标准 pattern: {name}/{name}_train_list.txt + videos_train/
    ann_train = root / f"{name}_train_list.txt"
    ann_val = root / f"{name}_val_list.txt"
    videos_train = root / "videos_train"
    videos_val = root / "videos_val"
    # fallback: pet_action_mammal_v0 pattern: annotation/{train,val}_public.txt + dataset/video/
    # 注意：ann_file 里路径是 dataset/video/XXX.mp4（相对数据集根），所以 data_prefix = 根目录
    if not ann_train.is_file():
        ann_train = root / "annotation" / "train_public.txt"
    if not ann_val.is_file():
        ann_val = root / "annotation" / "val_public.txt"
    if not videos_train.is_dir():
        videos_train = root  # 数据集根目录（ann_file 的相对路径已含 dataset/video/）
    if not videos_val.is_dir():
        videos_val = root
    return (
        str(ann_train) if ann_train.is_file() else "",
        str(videos_train) if videos_train.is_dir() else "",
        str(ann_val) if ann_val.is_file() else "",
        str(videos_val) if videos_val.is_dir() else "",
    )


def build_train_command(args, ann_train: str, videos_train: str, ann_val: str, videos_val: str) -> list[str]:
    cfg_path = args.mmaction2_config
    if not os.path.isabs(cfg_path):
        cfg_path = resolve_mmaction2_config(cfg_path)
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
        # AccMetric topk: avoid meaningless top5 on small datasets (top5 always 1.0 when classes < 5)
        ks = tuple(k for k in (1, 5) if k <= n_cls)  # n_cls=2 → (1,), n_cls=10 → (1,5)
        cfg_options.append(f"val_evaluator.metric_options.top_k_accuracy.topk={ks}")
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

    # VisSamplesHook 路径覆盖（hook 本身在 config 里注册）
    if ann_val:
        ds_root = os.path.dirname(os.path.dirname(ann_val))
        vis_interval = getattr(args, "vis_interval", 10)
        cfg_options.append(f"custom_hooks.0.interval={vis_interval}")
        cfg_options.append(f"custom_hooks.0.ann_file={ann_val}")
        cfg_options.append(f"custom_hooks.0.data_root={videos_val or videos_train}")
        cfg_options.append(f"custom_hooks.0.dataset_root={ds_root}")

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
        "name": f"{model_id} ({dataset_id}, epoch {epoch})" if dataset_id else f"{model_id} (epoch {epoch})",
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


def _generate_vis_samples(
    work_dir: str, cfg_path: str, ckpt_path: str,
    ann_file: str, data_root: str, num_samples: int = 6,
    epoch: int = 0, num_classes: int = None,
):
    """训练中/后对 val 样本生成可视化图（中间帧 + margin GT+pred+top5），存 work_dir/vis_samples/epoch_N/。"""
    import cv2
    try:
        from mmaction.apis import init_recognizer, inference_recognognizer
        from mmengine.config import Config
    except ImportError:
        log("", "[vis] mmaction 不可用，跳过可视化")
        return

    if not os.path.isfile(ann_file):
        return
    # 读 val 样本
    samples = []
    with open(ann_file, "r") as f:
        for ln in f:
            parts = ln.strip().split()
            if len(parts) >= 2:
                samples.append((parts[0], int(parts[1])))
    if not samples:
        return
    # 取前 N + 均匀采样
    step = max(1, len(samples) // num_samples)
    picked = samples[::step][:num_samples]

    # 读 label_map
    labels = []
    base = os.path.dirname(os.path.dirname(ann_file))  # dataset root
    for lm in [os.path.join(base, "annotation", "labels.txt"),
               os.path.join(base, "classes.txt")]:
        if os.path.isfile(lm):
            with open(lm) as f:
                labels = [ln.strip() for ln in f if ln.strip()]
            break

    vis_dir = os.path.join(work_dir, "vis_samples", f"epoch_{epoch}")
    os.makedirs(vis_dir, exist_ok=True)
    cfg = Config.fromfile(cfg_path)
    if num_classes is not None:
        cfg.model.cls_head.num_classes = num_classes
    model = init_recognizer(cfg, ckpt_path, device="cuda")
    font = cv2.FONT_HERSHEY_SIMPLEX

    results_meta = []
    for idx, (rel_path, gt_label) in enumerate(picked):
        video_path = os.path.join(data_root, rel_path) if not os.path.isabs(rel_path) else rel_path
        if not os.path.isfile(video_path):
            video_path = os.path.join(os.path.dirname(data_root), rel_path)
        if not os.path.isfile(video_path):
            continue
        try:
            result = inference_recognizer(model, video_path)
            scores = result.pred_score
            if hasattr(scores, "detach"):
                scores = scores.detach().cpu().numpy()
            import numpy as np
            scores = np.asarray(scores)
            top1_idx = int(scores.argmax())
            top1_score = float(scores[top1_idx])
            top1_label = labels[top1_idx] if top1_idx < len(labels) else str(top1_idx)
            gt_name = labels[gt_label] if gt_label < len(labels) else str(gt_label)

            # 取中间帧
            cap = cv2.VideoCapture(video_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 2:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                continue

            # 取 top5
            order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
            top5 = [(labels[i] if i < len(labels) else str(i), float(scores[i])) for i in order[:5]]

            # margin 布局
            h, w = frame.shape[:2]
            scale = max(0.4, min(w, h) / 700.0)
            thick = max(1, int(round(scale * 2)))
            line_h = max(18, int(24 * scale))
            top_h = max(30, line_h + 14)
            bottom_h = max(40, len(top5[:5]) * line_h + 12)
            canvas_h = h + top_h + bottom_h
            canvas = np.zeros((canvas_h, w, 3), dtype=np.uint8)
            canvas[top_h:top_h + h] = frame

            gt_text = f"GT: {gt_name}"
            pred_text = f"pred: {top1_label} ({top1_score:.2f})"
            pred_color = (0, 255, 0) if top1_idx == gt_label else (0, 0, 255)

            ty = top_h // 2 + line_h // 3
            cv2.putText(canvas, gt_text, (10, ty), font, scale, (0, 255, 0), thick, cv2.LINE_AA)
            (gw, _), _ = cv2.getTextSize(gt_text, font, scale, thick)
            cv2.putText(canvas, pred_text, (10 + gw + 20, ty), font, scale, pred_color, thick, cv2.LINE_AA)

            by = top_h + h + line_h
            for i, (lbl, sc) in enumerate(top5[:5]):
                cv2.putText(canvas, f"{i+1}. {lbl} {sc:.2f}", (10, by + i * line_h),
                            font, scale * 0.8, (255, 255, 255), max(1, thick - 1), cv2.LINE_AA)

            jpg_path = os.path.join(vis_dir, f"sample_{idx}.jpg")
            cv2.imwrite(jpg_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
            results_meta.append({
                "idx": idx, "file": f"sample_{idx}.jpg",
                "gt_label": gt_name, "pred_label": top1_label,
                "score": round(top1_score, 3), "correct": top1_idx == gt_label,
            })
        except Exception as e:
            log("", f"[vis] sample {idx} 失败: {e}")

    # 存元数据
    if results_meta:
        meta_path = os.path.join(vis_dir, "meta.json")
        with open(meta_path, "w") as f:
            json.dump({"epoch": epoch, "samples": results_meta}, f, ensure_ascii=False, indent=2)
        log("", f"[vis] epoch {epoch}: 生成 {len(results_meta)} 张可视化样本 → vis_samples/epoch_{epoch}/")

    return results_meta


def main() -> int:
    parser = argparse.ArgumentParser(description="mmaction2 training wrapper for pet-action-recognition")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--name", default=None, help="进程名称（快速标识用途）")
    parser.add_argument("--description", default=None, help="进程描述（备注）")
    parser.add_argument("--mmaction2-config", required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("-r", "--resume", default=None, help="resume from checkpoint path or 'auto' — 直接接入原 run 进程，恢复 epoch/optimizer/scheduler，继续跑完")
    parser.add_argument("-l", "--load-from", default=None, help="load checkpoint weights (path or run_id) — 只引入参数作为预训练权重，epoch=0 从头训练")
    parser.add_argument("-p", "--pretrained", default=None, help="backbone pretrained weights URL or local path (e.g. mmaction2 model zoo) — finetune")
    parser.add_argument("-s", "--from-scratch", action="store_true", help="train from random init, disable any pretrained weights in config")
    parser.add_argument("--vis-interval", type=int, default=10, help="可视化样本生成间隔（每 N epoch）")
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
        "name": args.name or args.run_id,
        "description": args.description or "",
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
        # 训练后生成可视化样本（补生成；训练中 Hook 已按 vis_interval 生成）
        best_ckpt = os.path.join(work_dir, "best_acc_top1_epoch_*.pth")
        import glob
        best_files = sorted(glob.glob(best_ckpt))
        vis_ckpt = best_files[-1] if best_files else (latest or "")
        if vis_ckpt:
            log(args.run_id, f"[vis] 训练后补生成可视化样本 (ckpt={vis_ckpt})...")
            vis_ann, vis_data = ann_val, videos_val
            if not vis_ann and args.dataset_id != QUADRUPED_DATASET_NAME:
                root = REPO / "datasets" / args.dataset_id
                vis_ann = str(root / "annotation" / "val_public.txt") if (root / "annotation" / "val_public.txt").is_file() else ""
                vis_data = str(root)
            if vis_ann and vis_data:
                try:
                    _generate_vis_samples(work_dir, resolve_mmaction2_config(args.mmaction2_config), vis_ckpt, vis_ann, vis_data, epoch=args.epochs, num_classes=args.num_classes)
                except Exception as e:
                    log(args.run_id, f"[vis] 训练后补生成失败（Hook 可能已生成）: {e}")
            else:
                log(args.run_id, "[vis] 无 val 标注文件，跳过")
    else:
        run["status"] = "error"
        run["metrics"]["returncode"] = ret
        log(args.run_id, f"[error] 训练进程退出码 {ret}")

    upsert_run(run)
    return ret


if __name__ == "__main__":
    sys.exit(main())
