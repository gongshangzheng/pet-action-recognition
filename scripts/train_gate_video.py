#!/usr/bin/env python3
"""Train an X3D-XS RGB presence gate on the first human-labeled clip pilot.

The input is a gate review set produced by ``prepare_gate_video_pilot.py``.
The run uses human labels only, samples four RGB frames from each two-second
proxy clip, and reports frozen-threshold results by split and domain.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "models" / "mmaction2") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "models" / "mmaction2"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(review_root: Path, labels_path: Path) -> list[dict]:
    """Load and validate review items and complete human labels."""
    data = json.loads((review_root / "items.json").read_text(encoding="utf-8"))
    if data.get("mode") != "video":
        raise ValueError("review set is not video mode")
    items = data.get("items", [])
    with labels_path.open(encoding="utf-8", newline="") as stream:
        label_rows = list(csv.DictReader(stream))
    labels = {row["path"]: row for row in label_rows}
    if len(labels) != len(label_rows):
        raise ValueError("duplicate label paths")
    if len(items) != len(labels):
        raise ValueError(f"items={len(items)} labels={len(labels)}; labels must be complete")

    rows = []
    source_splits: dict[str, str] = {}
    video_splits: dict[str, str] = {}
    approved_scope = "any_pet_in_window"
    for item in items:
        path = item["path"]
        label_row = labels.get(path)
        if label_row is None:
            raise ValueError(f"missing label: {path}")
        label = label_row.get("human_label", "")
        if label not in {"present", "absent"}:
            raise ValueError(f"invalid or unresolved label for {path}: {label!r}")
        if item.get("label_scope") != approved_scope:
            raise ValueError(f"unsupported label_scope for {path}: {item.get('label_scope')!r}")
        split = item.get("split")
        if split not in {"train", "val", "test"}:
            raise ValueError(f"invalid split for {path}: {split!r}")
        source = item.get("source_id")
        if not source or not item.get("video") or not item.get("domain"):
            raise ValueError(f"missing source metadata: {path}")
        if source_splits.setdefault(source, split) != split:
            raise ValueError(f"source occurs in multiple splits: {source}")
        video = item["video"]
        if video_splits.setdefault(video, split) != split:
            raise ValueError(f"source video occurs in multiple splits: {video}")
        video_path = review_root / item["file"]
        if not video_path.is_file():
            raise ValueError(f"missing proxy video: {video_path}")
        rows.append({
            **item,
            "human_label": label,
            "label": 1 if label == "present" else 0,
            "video_path": str(video_path),
        })
    return rows


class GateClips(Dataset):
    """Decode four uniformly spaced frames and apply clip-consistent transforms."""

    MEAN = np.array([114.75, 114.75, 114.75], dtype=np.float32)
    STD = np.array([57.38, 57.38, 57.38], dtype=np.float32)

    def __init__(self, rows: list[dict], frames: int, height: int, width: int,
                 train: bool, seed: int) -> None:
        self.rows = rows
        self.frames = frames
        self.height = height
        self.width = width
        self.train = train
        self.seed = seed
        self.epoch = 1

    def __len__(self) -> int:
        return len(self.rows)

    def _decode(self, path: str, index: int) -> np.ndarray:
        from decord import VideoReader

        reader = VideoReader(path, num_threads=1)
        count = len(reader)
        if count < self.frames:
            raise ValueError(f"clip has {count} frames, need >= {self.frames}: {path}")
        positions = np.linspace(0, count - 1, self.frames, dtype=np.int64)
        clip = reader.get_batch(positions).asnumpy()
        if clip.shape[:3] != (self.frames, *clip.shape[1:3]) or clip.ndim != 4:
            raise ValueError(f"unexpected clip shape {clip.shape}: {path}")
        return np.ascontiguousarray(clip)

    def _resize_letterbox(self, clip: np.ndarray) -> np.ndarray:
        import cv2

        source_h, source_w = clip.shape[1:3]
        scale = min(self.height / source_h, self.width / source_w)
        resize_h = max(1, int(round(source_h * scale)))
        resize_w = max(1, int(round(source_w * scale)))
        output = np.zeros((clip.shape[0], self.height, self.width, 3), dtype=np.uint8)
        for frame_index, frame in enumerate(clip):
            resized = cv2.resize(frame, (resize_w, resize_h), interpolation=cv2.INTER_AREA)
            top = (self.height - resize_h) // 2
            left = (self.width - resize_w) // 2
            output[frame_index, top:top + resize_h, left:left + resize_w] = resized
        return output

    def __getitem__(self, index: int):
        row = self.rows[index]
        clip = self._decode(row["video_path"], index)
        if self.train:
            generator = random.Random(self.seed * 1_000_003 + self.epoch * 1_000_019 + index)
            if generator.random() < 0.5:
                clip = clip[:, :, ::-1, :]
            brightness = 1.0 + generator.uniform(-0.15, 0.15)
            contrast = 1.0 + generator.uniform(-0.15, 0.15)
            mean_before = float(clip.mean()) / 255.0
            adjusted = clip.astype(np.float32) * contrast + (brightness - contrast) * 255.0 * mean_before
            clip = np.clip(adjusted, 0, 255).astype(np.uint8)
        clip = self._resize_letterbox(np.ascontiguousarray(clip)).astype(np.float32)
        clip = (clip - self.MEAN) / self.STD
        tensor = torch.from_numpy(clip).permute(3, 0, 1, 2).float()
        return tensor, torch.tensor(row["label"], dtype=torch.long)

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch


def build_x3d_xs(num_classes: int = 2):
    from mmaction.registry import MODELS
    import mmaction.models  # noqa: F401

    backbone = MODELS.build(dict(type="X3D", gamma_w=1, gamma_b=2.25, gamma_d=2.2))
    head = MODELS.build(dict(
        type="X3DHead", in_channels=432, num_classes=num_classes,
        spatial_type="avg", dropout_ratio=0.5, fc1_bias=False,
    ))
    return backbone, head


class X3DPresence(torch.nn.Module):
    def __init__(self, backbone, head) -> None:
        super().__init__()
        self.backbone = backbone
        self.head = head

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(inputs))


def load_pretrained(model: X3DPresence, checkpoint: Path) -> dict:
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    state = state.get("state_dict", state)
    backbone_state = {key.removeprefix("backbone."): value for key, value in state.items()
                      if key.startswith("backbone.")}
    head_fc1 = state.get("cls_head.fc1.weight")
    result = model.backbone.load_state_dict(backbone_state, strict=True)
    if head_fc1 is not None:
        model.head.fc1.weight.data.copy_(head_fc1)
    return {"checkpoint_sha256": sha256(checkpoint),
            "backbone_missing": list(result.missing_keys),
            "backbone_unexpected": list(result.unexpected_keys),
            "classifier_initialized": "random",
            "pretrain_fc1_loaded": head_fc1 is not None}


def metrics_at(probabilities: list[float], targets: list[int], threshold: float) -> dict:
    tp = sum(y == 1 and p >= threshold for p, y in zip(probabilities, targets))
    fn = sum(y == 1 and p < threshold for p, y in zip(probabilities, targets))
    fp = sum(y == 0 and p >= threshold for p, y in zip(probabilities, targets))
    tn = sum(y == 0 and p < threshold for p, y in zip(probabilities, targets))
    n = len(targets)
    recall = tp / max(1, tp + fn)
    specificity = tn / max(1, tn + fp)
    return {
        "n": n, "present": tp + fn, "absent": fp + tn,
        "accuracy": (tp + tn) / n if n else None,
        "recall": recall, "fpr": fp / max(1, fp + tn),
        "precision": tp / max(1, tp + fp),
        "balanced_accuracy": (recall + specificity) / 2,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def choose_threshold(probabilities: list[float], targets: list[int], target_miss: float) -> float:
    candidates = sorted(set(probabilities) | {0.0, 1.0}, reverse=True)
    for threshold in candidates:
        if metrics_at(probabilities, targets, threshold)["recall"] >= 1.0 - target_miss:
            return threshold
    return 0.0


def evaluate(model, loader, device) -> tuple[list[float], list[int]]:
    model.eval()
    probabilities, targets = [], []
    with torch.no_grad():
        for inputs, labels in loader:
            logits = model(inputs.to(device, non_blocking=True))
            probabilities.extend(torch.softmax(logits, dim=1)[:, 1].cpu().tolist())
            targets.extend(labels.tolist())
    return probabilities, targets


def forward_speed_ms(model, loader, device, repetitions: int = 20) -> dict:
    model.eval()
    cuda_device = torch.device(device)
    with torch.no_grad():
        batch = next(iter(loader))[0].to(device)
        for _ in range(3):
            model(batch)
        if device.startswith("cuda"):
            torch.cuda.synchronize(cuda_device)
        clip_samples = []
        for _ in range(repetitions):
            start = time.perf_counter()
            model(batch)
            if device.startswith("cuda"):
                torch.cuda.synchronize(cuda_device)
            clip_samples.append((time.perf_counter() - start) * 1000 / batch.shape[0])
    clip_samples.sort()
    p50 = clip_samples[len(clip_samples) // 2]
    p90 = clip_samples[min(len(clip_samples) - 1, math.ceil(0.9 * len(clip_samples)))]
    return {"p50_ms_per_clip": p50, "p90_ms_per_clip": p90,
            "p50_ms_per_frame": p50 / batch.shape[2],
            "p90_ms_per_frame": p90 / batch.shape[2],
            "frames_per_clip": int(batch.shape[2]), "batch_size": int(batch.shape[0]),
            "scope": "model_forward_only"}


def write_report(out: Path, report: dict) -> None:
    lines = ["# Gate video pilot metrics", "",
             f"- model: `{report['model']}`",
             f"- input: `{report['input_shape']}`",
             f"- selected epoch: {report['threshold']['selected_epoch']}",
             f"- frozen threshold: {report['threshold']['threshold']:.6f}", "",
             "| split/domain | n | present/absent | accuracy | recall | FPR | TP/FP/FN/TN |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for name, cell in report["domains"].items():
        lines.append(f"| {name} | {cell['n']} | {cell['present']}/{cell['absent']} | "
                     f"{cell['accuracy']:.3f} | {cell['recall']:.3f} | {cell['fpr']:.3f} | "
                     f"{cell['tp']}/{cell['fp']}/{cell['fn']}/{cell['tn']} |")
    speed = report["forward_speed_ms"]
    lines.extend(["", f"Forward speed (decode/preprocess excluded): p50 {speed['p50_ms_per_clip']:.3f} ms/clip "
                      f"({speed['p50_ms_per_frame']:.3f} ms/frame), p90 {speed['p90_ms_per_clip']:.3f} ms/clip "
                      f"({speed['p90_ms_per_frame']:.3f} ms/frame).", ""])
    (out / "metrics.md").write_text("\n".join(lines), encoding="utf-8")


def train_step(model, inputs, labels, optimizer, criterion) -> float:
    optimizer.zero_grad(set_to_none=True)
    loss = criterion(model(inputs), labels)
    loss.backward()
    optimizer.step()
    return float(loss.detach()) * inputs.size(0)


def dataloader_worker_init(_: int) -> None:
    import cv2

    cv2.setNumThreads(1)


def write_predictions(path: Path, rows: list[dict], probabilities: list[float],
                      targets: list[int]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row, probability, target in zip(rows, probabilities, targets):
            stream.write(json.dumps({
                "path": row["path"], "source_id": row["source_id"], "video": row["video"],
                "start_sec": row.get("start_sec"), "end_sec": row.get("end_sec"),
                "domain": row["domain"], "prob": round(probability, 6), "label": target,
            }, ensure_ascii=False) + "\n")


def build_eval_binding(args, best_path: Path, threshold_path: Path) -> dict:
    return {
        "labels_sha256": sha256(args.labels),
        "items_sha256": sha256(args.review_root / "items.json"),
        "pretrain_checkpoint_sha256": sha256(args.checkpoint),
        "best_checkpoint_sha256": sha256(best_path),
        "threshold_sha256": sha256(threshold_path),
        "frames": args.frames, "height": args.height, "width": args.width,
        "seed": args.seed, "batch_size": args.batch,
    }


def validate_eval_binding(training_report: dict, args, best_path: Path,
                          threshold_path: Path) -> None:
    expected = training_report.get("eval_binding")
    if not isinstance(expected, dict):
        raise ValueError("train_metrics.json lacks eval_binding")
    actual = build_eval_binding(args, best_path, threshold_path)
    mismatches = [key for key, value in expected.items() if actual.get(key) != value]
    if mismatches:
        raise ValueError(f"finalization inputs differ from training: {', '.join(mismatches)}")


def claim_finalization(out: Path) -> None:
    if (out / "metrics.json").is_file() or (out / "predictions_test.jsonl").is_file():
        raise FileExistsError("final test evaluation already exists; refuse to overwrite it")
    marker = out / "finalization.lock"
    try:
        descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise FileExistsError("another finalization process owns this run") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "created_at": time.time_ns()}, stream)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=4)
    parser.add_argument("--height", type=int, default=160)
    parser.add_argument("--width", type=int, default=288)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--target-miss", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--device", default="cuda:1" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--eval-only", action="store_true",
                        help="load best.pt and frozen threshold, then run the one-time val/test finalization")
    args = parser.parse_args()

    import cv2

    cv2.setNumThreads(1)
    torch.set_num_threads(int(os.environ.get("TORCH_NUM_THREADS", "2")))
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    rows = load_rows(args.review_root, args.labels)
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "val"]
    test_rows = [row for row in rows if row["split"] == "test"]
    print("[gate-video] split", {name: len(group) for name, group in
          [("train", train_rows), ("val", val_rows), ("test", test_rows)]}, flush=True)
    print("[gate-video] labels", dict(Counter(row["human_label"] for row in rows)), flush=True)

    val_dataset = GateClips(val_rows, args.frames, args.height, args.width, False, args.seed)
    test_dataset = GateClips(test_rows, args.frames, args.height, args.width, False, args.seed)
    loaders = {
        "val": DataLoader(val_dataset, batch_size=args.batch, shuffle=False,
                          num_workers=args.workers, pin_memory=True,
                          worker_init_fn=dataloader_worker_init),
        "test": DataLoader(test_dataset, batch_size=args.batch, shuffle=False,
                           num_workers=args.workers, pin_memory=True,
                           worker_init_fn=dataloader_worker_init),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.out / "best.pt"
    if args.eval_only:
        required = [checkpoint_path, args.out / "threshold.json", args.out / "train_metrics.json"]
        if not all(path.is_file() for path in required):
            raise ValueError("eval-only requires best.pt, threshold.json, and train_metrics.json")
        train_report = json.loads((args.out / "train_metrics.json").read_text(encoding="utf-8"))
        frozen = json.loads((args.out / "threshold.json").read_text(encoding="utf-8"))
        threshold = frozen["threshold"]
        validate_eval_binding(train_report, args, checkpoint_path, args.out / "threshold.json")
        claim_finalization(args.out)
        backbone, head = build_x3d_xs()
        model = X3DPresence(backbone, head).to(args.device)
        model.load_state_dict(torch.load(checkpoint_path, map_location=args.device, weights_only=True))
        report = {**train_report, "threshold": frozen, "domains": {}}
    else:
        if checkpoint_path.exists() or (args.out / "threshold.json").exists():
            raise FileExistsError("training artifacts already exist; use a new run directory")
        train_dataset = GateClips(train_rows, args.frames, args.height, args.width, True, args.seed)
        class_counts = Counter(row["label"] for row in train_rows)
        weights = [1.0 if row["label"] == 1 else class_counts[1] / max(1, class_counts[0])
                   for row in train_rows]
        sampler = WeightedRandomSampler(weights, num_samples=len(train_rows), replacement=True)
        train_loader = DataLoader(train_dataset, batch_size=args.batch, sampler=sampler,
                                  num_workers=args.workers, pin_memory=True, drop_last=True,
                                  worker_init_fn=dataloader_worker_init)
        backbone, head = build_x3d_xs()
        model = X3DPresence(backbone, head).to(args.device)
        load_info = load_pretrained(model, args.checkpoint)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
        criterion = torch.nn.CrossEntropyLoss()

        best = {"epoch": 0, "balanced_accuracy": -1.0}
        for epoch in range(1, args.epochs + 1):
            model.train()
            train_dataset.set_epoch(epoch)
            running_loss = 0.0
            for inputs, labels in train_loader:
                running_loss += train_step(
                    model, inputs.to(args.device, non_blocking=True),
                    labels.to(args.device, non_blocking=True), optimizer, criterion,
                )
            scheduler.step()
            probabilities, targets = evaluate(model, loaders["val"], args.device)
            score = metrics_at(probabilities, targets, 0.5)["balanced_accuracy"]
            print(f"[gate-video] epoch {epoch}/{args.epochs} loss {running_loss / len(train_rows):.4f} "
                  f"val balanced_acc@0.5 {score:.3f}", flush=True)
            if score > best["balanced_accuracy"]:
                best = {"epoch": epoch, "balanced_accuracy": score}
                torch.save(model.state_dict(), checkpoint_path)

        model.load_state_dict(torch.load(checkpoint_path, map_location=args.device, weights_only=True))
        val_prob, val_target = evaluate(model, loaders["val"], args.device)
        threshold = choose_threshold(val_prob, val_target, args.target_miss)
        val_metrics = metrics_at(val_prob, val_target, threshold)
        frozen = {"threshold": threshold, "target_miss": args.target_miss,
                  "selection_metric": "balanced_accuracy_at_0.5",
                  "selected_epoch": best["epoch"], "val": val_metrics}
        threshold_path = args.out / "threshold.json"
        threshold_path.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = {
            "model": "X3D-XS", "input_shape": f"RGB {args.frames}x{args.height}x{args.width}",
            "label_scope": rows[0]["label_scope"], "seed": args.seed,
            "epochs": args.epochs, "batch_size": args.batch, "learning_rate": args.lr,
            "class_balanced_training": "inverse_class_frequency_weighted_sampler",
            "pretrained_checkpoint": str(args.checkpoint), "pretrain_load": load_info,
            "labels_sha256": sha256(args.labels),
            "items_sha256": sha256(args.review_root / "items.json"), "threshold": frozen,
            "eval_binding": build_eval_binding(args, checkpoint_path, threshold_path),
        }
        (args.out / "train_metrics.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.out / "execution_status").write_text("training_and_threshold_complete\n", encoding="utf-8")
        print(f"[gate-video] training complete; threshold={threshold:.6f} "
              f"selected_epoch={best['epoch']}; run eval-only once for frozen test", flush=True)
        return 0

    for split in ("val", "test"):
        probabilities, targets = evaluate(model, loaders[split], args.device)
        split_rows = {"val": val_rows, "test": test_rows}[split]
        report["domains"][f"{split}/all"] = metrics_at(probabilities, targets, threshold)
        for domain in ("day", "night"):
            indexes = [i for i, row in enumerate(split_rows) if row["domain"] == domain]
            if indexes:
                report["domains"][f"{split}/{domain}"] = metrics_at(
                    [probabilities[i] for i in indexes], [targets[i] for i in indexes], threshold)
        write_predictions(args.out / f"predictions_{split}.jsonl", split_rows, probabilities, targets)
    report["forward_speed_ms"] = forward_speed_ms(model, loaders["val"], args.device)
    (args.out / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "summary.json").write_text(json.dumps({
        "status": "completed", "run": "video-pilot-x3d-xs", "model": "X3D-XS",
        "threshold": threshold, "selected_epoch": frozen["selected_epoch"],
        "val": report["domains"]["val/all"], "test": report["domains"]["test/all"],
        "forward_speed_ms": report["forward_speed_ms"],
        "labels_sha256": report["labels_sha256"], "items_sha256": report["items_sha256"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.out, report)
    (args.out / "execution_status").write_text("completed\n", encoding="utf-8")
    print(f"[gate-video] threshold={threshold:.6f} selected_epoch={frozen['selected_epoch']}", flush=True)
    for name, cell in report["domains"].items():
        print(f"[gate-video] {name:12s} n={cell['n']:3d} acc={cell['accuracy']:.3f} "
              f"recall={cell['recall']:.3f} fpr={cell['fpr']:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
