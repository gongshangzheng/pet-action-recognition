#!/usr/bin/env python3
"""生成最小的合成四足动作数据集，用于 mmaction2 训练冒烟测试。"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2
import numpy as np


CLASSES = ["sit", "walk"]


def make_video(path: str, label: int, n_frames: int = 30, size: int = 64) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 10.0, (size, size))
    if not writer.isOpened():
        raise RuntimeError(f"无法打开 VideoWriter: {path}")
    for t in range(n_frames):
        # 不同类别用不同颜色/运动模式，保证可区分
        if label == 0:  # sit: 静态偏红
            frame = np.full((size, size, 3), (80, 50, 180), dtype=np.uint8)
        else:  # walk: 移动绿条
            frame = np.full((size, size, 3), (60, 120, 60), dtype=np.uint8)
            x = int((t / n_frames) * (size - 10))
            frame[:, x : x + 8] = (200, 200, 200)
        writer.write(frame)
    writer.release()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="datasets/quadruped_action")
    parser.add_argument("--train-per-class", type=int, default=4)
    parser.add_argument("--val-per-class", type=int, default=2)
    parser.add_argument("--test-per-class", type=int, default=2)
    args = parser.parse_args()

    root = Path(args.root)
    (root / "videos_train").mkdir(parents=True, exist_ok=True)
    (root / "videos_val").mkdir(parents=True, exist_ok=True)
    (root / "videos_test").mkdir(parents=True, exist_ok=True)

    with open(root / "classes.txt", "w", encoding="utf-8") as f:
        for c in CLASSES:
            f.write(c + "\n")

    def write_split(split: str, per_class: int) -> None:
        ann_path = root / f"{root.name}_{split}_list.txt"
        with open(ann_path, "w", encoding="utf-8") as f:
            for label, cls in enumerate(CLASSES):
                for i in range(per_class):
                    name = f"{cls}_{i+1:03d}.mp4"
                    video_path = root / f"videos_{split}" / name
                    make_video(str(video_path), label)
                    # VideoDataset 的 ann_file 路径相对于 data_prefix.video（即 videos_{split}/）
                    f.write(f"{name} {label}\n")

    write_split("train", args.train_per_class)
    write_split("val", args.val_per_class)
    write_split("test", args.test_per_class)
    print(f"已生成合成数据集：{root}")


if __name__ == "__main__":
    main()
