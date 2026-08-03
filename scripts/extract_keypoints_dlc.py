#!/usr/bin/env python3
"""DeepLabCut SuperAnimal-Quadruped 骨架关键点批量提取。

用 SuperAnimal-Quadruped 零样本模型（hrnet_w32 + fasterrcnn 检测器，39 关键点）
对视频批量提取骨架序列，每段视频存一个 .npz，供后续转 mmaction2 skeleton 格式
训练 PoseC3D。

注意：本脚本运行在 pet 的 `dlc` conda env（不是 mmaction2 的 `pet` env）：
  ~/miniconda3/envs/dlc/bin/python scripts/extract_keypoints_dlc.py \
    --ann-file datasets/pet_action_mammal_v0/annotation/train_public.txt \
    --data-root datasets/pet_action_mammal_v0 \
    --device cuda:1 --batch-size 8 --detector-batch-size 4

模型快照已预置在 dlc env 的 modelzoo/checkpoints/（hf_hub_download 在 pet 上有
元数据兼容问题，需手工 curl 下载，见 tasks.json t10 进展记录）。

产物（--out-dir，默认 <data-root>/keypoints_dlc/）：
  <video_stem>.npz:
    keypoint       (T, K, 2) float32   像素坐标（无检测 -> 0）
    keypoint_score (T, K)    float32   置信度 [0,1]（无检测 -> 0）
    bodyparts      (K,)      str       关键点名（SuperAnimal-Quadruped 39 点）
    label          int                 来自 ann_file（无则 -1）
    video          str                 相对 data-root 的视频路径
  _summary.json                        运行统计（ok/failed + 每视频 det_rate/mean_conf）

实现说明：使用低层 API（get_inference_runners + video_inference），模型只加载一次，
逐视频推理 + try/except 隔离——整段零检测的视频会产生空预测（高层批接口会因此
np.stack 崩溃、毒化整个 chunk），这里对其输出全零 npz（det_rate=0，下游可过滤）。
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

SUPERANIMAL_NAME = "superanimal_quadruped"
MODEL_NAME = "hrnet_w32"
DETECTOR_NAME = "fasterrcnn_resnet50_fpn_v2"
NUM_BODYPARTS = 39


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DLC SuperAnimal-Quadruped keypoint extraction")
    p.add_argument("--videos", nargs="*", default=None, help="显式视频路径列表")
    p.add_argument("--ann-file", default=None, help="VideoDataset manifest（每行: <相对路径> <label>）")
    p.add_argument("--data-root", default="datasets/pet_action_mammal_v0")
    p.add_argument("--out-dir", default=None, help="默认 <data-root>/keypoints_dlc")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--batch-size", type=int, default=8, help="pose 模型 batch size")
    p.add_argument("--detector-batch-size", type=int, default=4)
    p.add_argument("--max-individuals", type=int, default=1, help="每帧保留的个体数（取置信度最高者）")
    p.add_argument("--limit", type=int, default=None, help="只处理前 N 段（调试用）")
    p.add_argument("--force", action="store_true", help="重跑已存在 npz 的视频")
    return p.parse_args()


def collect_videos(args: argparse.Namespace) -> list[tuple[str, int]]:
    """返回 [(abs_video_path, label)]。"""
    if args.videos:
        return [(str(Path(v).resolve()), -1) for v in args.videos]
    root = Path(args.data_root)
    items = []
    with open(args.ann_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rel, label = line.rsplit(" ", 1)
            items.append((str(root / rel), int(label)))
    return items


def preds_to_arrays(preds: list[dict], n_frames_hint: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """逐帧预测 -> (T,K,2), (T,K)。每帧取 mean likelihood 最高的个体；无检测为 0。"""
    T = len(preds) or n_frames_hint
    keypoint = np.zeros((T, NUM_BODYPARTS, 2), dtype=np.float32)
    scores = np.zeros((T, NUM_BODYPARTS), dtype=np.float32)
    for t, p in enumerate(preds):
        bp = np.asarray(p["bodyparts"])[..., :3]  # (N, K, 3)
        if bp.size == 0 or bp.shape[0] == 0:
            continue
        conf = np.clip(bp[..., 2], 0.0, 1.0)
        best = int(conf.mean(axis=1).argmax())
        K = min(NUM_BODYPARTS, bp.shape[1])
        keypoint[t, :K] = bp[best, :K, :2]
        scores[t, :K] = conf[best, :K]
    return keypoint, scores


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.data_root) / "keypoints_dlc"
    out_dir.mkdir(parents=True, exist_ok=True)

    items = collect_videos(args)
    if args.limit:
        items = items[: args.limit]
    todo = [(v, l) for v, l in items if args.force or not (out_dir / (Path(v).stem + ".npz")).is_file()]
    print(f"[info] 共 {len(items)} 段，待处理 {len(todo)} 段（跳过已完成 {len(items) - len(todo)}）")
    if not todo:
        return 0

    from deeplabcut.pose_estimation_pytorch.config.pose import PoseConfig
    from deeplabcut.pose_estimation_pytorch.modelzoo.inference import (
        get_inference_runners,
        video_inference,
    )
    from deeplabcut.pose_estimation_pytorch.modelzoo.utils import (
        get_super_animal_snapshot_path,
    )

    config = PoseConfig.build_for_superanimal_inference(
        super_animal=SUPERANIMAL_NAME,
        model_name=MODEL_NAME,
        detector_name=DETECTOR_NAME,
        max_individuals=args.max_individuals,
        device=args.device,
    )
    bodyparts = list(config.get("metadata", {}).get("bodyparts", [])) or [
        f"bp{i}" for i in range(NUM_BODYPARTS)
    ]
    pose_path = get_super_animal_snapshot_path(SUPERANIMAL_NAME, MODEL_NAME)
    det_path = get_super_animal_snapshot_path(SUPERANIMAL_NAME, DETECTOR_NAME)
    pose_runner, det_runner = get_inference_runners(
        model_config=config,
        snapshot_path=pose_path,
        detector_path=det_path,
        batch_size=args.batch_size,
        detector_batch_size=args.detector_batch_size,
        device=args.device,
    )
    print(f"[info] 模型已加载（{len(bodyparts)} 关键点），开始逐视频推理", flush=True)

    # 合并已有 summary（断点续跑）
    summary_path = out_dir / "_summary.json"
    stats = {"ok": 0, "failed": [], "videos": {}}
    if summary_path.is_file():
        try:
            stats.update(json.loads(summary_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    stats["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    data_root = str(Path(args.data_root).resolve())
    t0 = time.time()
    for i, (video, label) in enumerate(todo):
        stem = Path(video).stem
        try:
            preds = video_inference(video, pose_runner, det_runner)
            keypoint, scores = preds_to_arrays(preds)
            np.savez_compressed(
                out_dir / f"{stem}.npz",
                keypoint=keypoint,
                keypoint_score=scores,
                bodyparts=np.array(bodyparts),
                label=np.int64(label),
                video=np.array(
                    str(Path(video).relative_to(data_root)) if str(video).startswith(data_root) else str(video)
                ),
            )
            stats["ok"] += 1
            stats["videos"][stem] = {
                "frames": int(keypoint.shape[0]),
                "det_rate": round(float((scores.max(axis=1) > 0.1).mean()), 3) if scores.shape[0] else 0.0,
                "mean_conf": round(float(scores.mean()), 3),
            }
        except Exception as e:  # noqa: BLE001 - 逐视频隔离，失败不影响其他
            print(f"[error] {stem}: {type(e).__name__}: {e}", flush=True)
            stats["failed"].append(video)
            stats["videos"][stem] = {"frames": 0, "det_rate": 0.0, "mean_conf": 0.0, "error": str(e)[:200]}

        if (i + 1) % 20 == 0 or i + 1 == len(todo):
            dt = time.time() - t0
            eta = dt / (i + 1) * (len(todo) - i - 1)
            stats["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            summary_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[progress] {i + 1}/{len(todo)} ok={stats['ok']} failed={len(stats['failed'])} "
                  f"elapsed={dt / 60:.1f}min eta={eta / 60:.1f}min", flush=True)

    print(f"[done] ok={stats['ok']} failed={len(stats['failed'])} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
