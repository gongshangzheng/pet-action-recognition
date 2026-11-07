#!/usr/bin/env python3
"""Run the trained recognizer on one clip file and print per-class scores."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "models/mmaction2"))

import torch
import cv2
import numpy as np
from mmengine.config import Config
from mmaction.registry import MODELS, TRANSFORMS, register_all_modules

register_all_modules(init_default_scope=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--interval", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = Config.fromfile(str(args.config))
    classes = cfg.classes
    model = MODELS.build(cfg.model)
    state = torch.load(str(args.checkpoint), map_location="cpu", weights_only=False)
    model.load_state_dict(state["state_dict"], strict=True)
    model.eval()

    capture = cv2.VideoCapture(str(args.clip))
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames:
        raise RuntimeError(f"no frames decoded from {args.clip}")
    total = len(frames)
    indices = np.linspace(0, total - 1, args.frames, dtype=int)
    picked = [frames[i] for i in indices]

    resized = []
    for frame in picked:
        h, w = frame.shape[:2]
        scale = 256 / min(h, w)
        img = cv2.resize(frame, (int(w * scale), int(h * scale)))
        hh, ww = img.shape[:2]
        top, left = (hh - 224) // 2, (ww - 224) // 2
        img = img[top:top + 224, left:left + 224]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406]); std = np.array([0.229, 0.224, 0.225])
        img = (img - mean) / std
        resized.append(img)
    tensor = torch.from_numpy(np.stack(resized)).permute(3, 0, 1, 2).unsqueeze(0)
    with torch.no_grad():
        scores = model(tensor, mode="predict")[0].pred_score
    top = torch.topk(scores, k=min(5, len(scores)))
    print("clip:", args.clip.name)
    for score, idx in zip(top.values.tolist(), top.indices.tolist()):
        print(f"  {classes[idx]:22s} {score * 100:6.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
