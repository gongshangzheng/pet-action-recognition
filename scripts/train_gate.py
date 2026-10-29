#!/usr/bin/env python3
"""训练在场门控（逐帧图像二分类）并做按域评测。

输入：`prepare_gate_frames.py` 的帧 + manifest，`label_gate_frames.py merge` 的标签。
输出：`<out>/` 下 best.pt、threshold.json、metrics.json、predictions_<split>.jsonl。

要点（对应 change design D10.3 / D6）：
- 单帧输入、无帧间状态；输入尺寸按 `calibrate_gate_resolution.py` 的标定结果选定。
- 正负 1:2 加权采样；增强只做几何 + 亮度对比度（不做强颜色抖动，避免破坏红外/彩色边界）。
- 阈值在 val 上按「漏检率 ≤ target」反解后**冻结**，test 只用冻结阈值评估。
- 指标一律按域（白天/夜视）分表。

用法：
  python scripts/train_gate.py --manifest results/gate/dataset_v1/manifest.csv \
      --labels results/gate/labels_merged.jsonl --image-root results/gate/dataset_v1 \
      --arch mobilenet_v3_small --img-size 448 --epochs 12 --out results/gate/runs/mnv3_s_448
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler


class GateFrames(Dataset):
    def __init__(self, rows: list[dict], image_root: Path, img_size: int, train: bool) -> None:
        from torchvision import transforms

        self.rows = rows
        self.image_root = image_root
        self.size = (img_size, int(round(img_size * 16 / 9)))   # (H, W)：整帧 16:9，不裁两侧
        if train:
            self.transform = transforms.Compose([
                transforms.RandomResizedCrop(self.size, scale=(0.6, 1.0), ratio=(1.4, 2.0)),
                transforms.RandomHorizontalFlip(),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        else:
            self.transform = transforms.Compose([
                transforms.Resize(self.size),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        from PIL import Image

        row = self.rows[index]
        image = Image.open(self.image_root / row["path"]).convert("RGB")
        return self.transform(image), torch.tensor(row["label"], dtype=torch.long)


def build_model(arch: str, pretrained: bool):
    from torchvision import models

    if arch == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 2)
    elif arch == "mobilenet_v3_large":
        weights = models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v3_large(weights=weights)
        model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 2)
    elif arch == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        model = models.resnet18(weights=weights)
        model.fc = torch.nn.Linear(model.fc.in_features, 2)
    else:
        raise ValueError(f"未知 arch: {arch}")
    return model


def load_rows(manifest: Path, labels: Path) -> list[dict]:
    with labels.open(encoding="utf-8") as stream:
        label_map = {json.loads(line)["path"]: json.loads(line) for line in stream if line.strip()}
    rows = []
    with manifest.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            label = label_map.get(row["path"])
            if label is None:
                continue
            rows.append({**row, "label": 1 if label["label"] == "present" else 0})
    return rows


def evaluate(model, loader, device) -> tuple[list[float], list[int], list[dict]]:
    model.eval()
    probabilities, targets, meta = [], [], []
    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            probs = torch.softmax(logits, dim=1)[:, 1]
            probabilities.extend(probs.cpu().tolist())
            targets.extend(labels.tolist())
    return probabilities, targets, meta


def metrics_at(probabilities: list[float], targets: list[int], threshold: float) -> dict:
    n = len(targets)
    tp = sum(1 for p, y in zip(probabilities, targets) if y == 1 and p >= threshold)
    fn = sum(1 for p, y in zip(probabilities, targets) if y == 1 and p < threshold)
    fp = sum(1 for p, y in zip(probabilities, targets) if y == 0 and p >= threshold)
    tn = sum(1 for p, y in zip(probabilities, targets) if y == 0 and p < threshold)
    return {
        "n": n,
        "recall": tp / max(1, tp + fn),
        "fpr": fp / max(1, fp + tn),
        "precision": tp / max(1, tp + fp),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arch", default="mobilenet_v3_small")
    parser.add_argument("--img-size", type=int, default=448)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--neg-ratio", type=float, default=2.0, help="负样本相对正样本的采样权重比")
    parser.add_argument("--target-miss", type=float, default=0.02, help="阈值反解目标：漏检率上限")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default=None)
    parser.add_argument("--workers", type=int, default=2, help="DataLoader 进程数（共享机默认 2）")
    parser.add_argument("--eval-only", action="store_true",
                        help="只加载 --out/best.pt 做阈值反解与按域评测（训练被中断后用）")
    args = parser.parse_args()

    # 共享机线程纪律：DataLoader worker + OpenMP 一起会把 CPU 顶穿
    # （实测 4 worker 时 CPU 391%、RSS 11.7GB，被 resource_guard 按 300% 上限终止）
    torch.set_num_threads(int(os.environ.get("TORCH_NUM_THREADS", "2")))
    try:
        import cv2
        cv2.setNumThreads(0)    # worker 内部不再并行，交给 DataLoader 的多进程
    except Exception:
        pass

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")

    rows = load_rows(args.manifest, args.labels)
    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    test_rows = [r for r in rows if r["split"] == "test"]
    if not train_rows or not val_rows:
        print("[train_gate] train/val 为空，检查 manifest 与 labels 的路径是否对齐")
        return 2
    pos = sum(r["label"] for r in train_rows)
    print(f"[train_gate] train {len(train_rows)}（正 {pos} / 负 {len(train_rows) - pos}）"
          f" val {len(val_rows)} test {len(test_rows)} | device {device}")

    train_set = GateFrames(train_rows, args.image_root, args.img_size, train=True)
    val_set = GateFrames(val_rows, args.image_root, args.img_size, train=False)
    test_set = GateFrames(test_rows, args.image_root, args.img_size, train=False)

    weights = [args.neg_ratio if r["label"] == 0 else 1.0 for r in train_rows]
    sampler = WeightedRandomSampler(weights, num_samples=len(train_rows), replacement=True)
    train_loader = DataLoader(train_set, batch_size=args.batch, sampler=sampler,
                              num_workers=args.workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_set, batch_size=args.batch, shuffle=False, num_workers=args.workers)
    test_loader = DataLoader(test_set, batch_size=args.batch, shuffle=False, num_workers=args.workers)

    model = build_model(args.arch, pretrained=True).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = torch.nn.CrossEntropyLoss()

    best = {"epoch": -1, "recall": -1.0}
    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.out / "best.pt"

    if args.eval_only:
        if not checkpoint_path.is_file():
            print(f"[train_gate] --eval-only 但找不到 {checkpoint_path}")
            return 2
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
        print(f"[train_gate] eval-only：已加载 {checkpoint_path}")
        best = {"epoch": -1, "recall": float("nan")}
    for epoch in range(1, 0 if args.eval_only else args.epochs + 1):
        model.train()
        running = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            running += float(loss) * images.size(0)
        scheduler.step()
        probabilities, targets, _ = evaluate(model, val_loader, device)
        recall_at_half = metrics_at(probabilities, targets, 0.5)["recall"]
        print(f"[train_gate] epoch {epoch}/{args.epochs} loss {running / max(1, len(train_set)):.4f} "
              f"val recall@0.5 {recall_at_half:.3f}", flush=True)
        if recall_at_half > best["recall"]:
            best = {"epoch": epoch, "recall": recall_at_half}
            torch.save(model.state_dict(), args.out / "best.pt")

    if not args.eval_only:
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))

    # 阈值反解：在 val 上按「漏检率 ≤ target_miss」找最低阈值（宁多跑不漏判）
    probabilities, targets, _ = evaluate(model, val_loader, device)
    # 在满足「漏检 <= target_miss」的阈值里取**最高**的那个：召回约束优先，同时最小化误检。
    # （取最低会退化成「全判有猫」，误检率 100%，门控失去早退价值。）
    chosen = 1.0
    for threshold in sorted(set(probabilities), reverse=True):
        if metrics_at(probabilities, targets, threshold)["recall"] >= 1.0 - args.target_miss:
            chosen = threshold
            break
    frozen = {"threshold": chosen, "target_miss": args.target_miss,
              "val": metrics_at(probabilities, targets, chosen), "selected_epoch": best["epoch"]}
    (args.out / "threshold.json").write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[train_gate] 冻结阈值 {chosen:.4f}（val 漏检 {1 - frozen['val']['recall']:.2%}）")

    report = {"arch": args.arch, "img_size": args.img_size, "seed": args.seed, "threshold": frozen, "domains": {}}
    for split, loader, split_rows in (("val", val_loader, val_rows), ("test", test_loader, test_rows)):
        probabilities, targets, _ = evaluate(model, loader, device)
        for domain in ("day", "night"):
            index = [i for i, r in enumerate(split_rows) if r["domain"] == domain]
            if not index:
                continue
            report["domains"][f"{split}/{domain}"] = metrics_at(
                [probabilities[i] for i in index], [targets[i] for i in index], chosen)
        report["domains"][f"{split}/all"] = metrics_at(probabilities, targets, chosen)
        with (args.out / f"predictions_{split}.jsonl").open("w", encoding="utf-8") as stream:
            for row, probability, target in zip(split_rows, probabilities, targets):
                stream.write(json.dumps({"path": row["path"], "domain": row["domain"],
                                         "prob": round(probability, 4), "label": target}, ensure_ascii=False) + "\n")

    (args.out / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[train_gate] 按域指标：")
    for key, cell in report["domains"].items():
        print(f"   {key:14s} n={cell['n']:5d} recall {cell['recall']:.3f} fpr {cell['fpr']:.3f}")
    print(f"[train_gate] 产物 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
