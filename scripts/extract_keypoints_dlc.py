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

首次运行会自动下载模型快照（HuggingFace，国内可设 HF_ENDPOINT=https://hf-mirror.com）。

产物（--out-dir，默认 <data-root>/keypoints_dlc/）：
  <video_stem>.npz:
    keypoint       (T, K, 2) float32   像素坐标（NaN -> 0）
    keypoint_score (T, K)    float32   置信度（缺失 -> 0）
    bodyparts      (K,)      str       关键点名（SuperAnimal-Quadruped 39 点）
    label          int                 来自 ann_file（无则 -1）
    video          str                 相对 data-root 的视频路径
  _summary.json                        本次运行统计（成功/失败/跳过）

--vis N：对前 N 段视频额外生成 DLC 标注视频到 --vis-dir（质量抽检用）。
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

SUPERANIMAL_NAME = "superanimal_quadruped"
MODEL_NAME = "hrnet_w32"
DETECTOR_NAME = "fasterrcnn_resnet50_fpn_v2"


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
    p.add_argument("--chunk", type=int, default=16, help="每次 DLC 调用处理的视频数（模型只加载一次）")
    p.add_argument("--limit", type=int, default=None, help="只处理前 N 段（调试用）")
    p.add_argument("--force", action="store_true", help="重跑已存在 npz 的视频")
    p.add_argument("--vis", type=int, default=0, help="前 N 段生成 DLC 标注视频（抽检）")
    p.add_argument("--vis-dir", default="results/skeleton/dlc_vis")
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


def df_to_arrays(df, max_individuals: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """DLC df_2d (scorer, individuals, bodyparts, coords) -> (T,K,2), (T,K), bodyparts。

    每帧取 mean likelihood 最高的个体。
    """
    cols = df.columns
    scorer = cols.get_level_values("scorer")[0]
    individuals = list(cols.get_level_values("individuals").unique())
    bodyparts = list(cols.get_level_values("bodyparts").unique())
    T, K = len(df), len(bodyparts)

    # (T, N, K, 3)
    arr = np.full((T, len(individuals), K, 3), np.nan, dtype=np.float32)
    for j, ind in enumerate(individuals):
        sub = df.loc[:, (scorer, ind)]
        for i, bp in enumerate(bodyparts):
            if (bp, "x") in sub.columns:
                arr[:, j, i, 0] = sub[(bp, "x")].to_numpy(dtype=np.float32)
                arr[:, j, i, 1] = sub[(bp, "y")].to_numpy(dtype=np.float32)
                arr[:, j, i, 2] = sub[(bp, "likelihood")].to_numpy(dtype=np.float32)

    # 选主个体：mean likelihood（缺失标记 -1 与 NaN 都视为 0）
    conf = np.nan_to_num(arr[..., 2], nan=0.0)
    conf = np.clip(conf, 0.0, 1.0)
    mean_conf = conf.mean(axis=2)  # (T, N)
    best = mean_conf.argmax(axis=1)  # (T,)
    keypoint = arr[np.arange(T), best][:, :K, :2]
    scores = conf[np.arange(T), best][:, :K]
    keypoint = np.nan_to_num(keypoint, nan=0.0)
    return keypoint.astype(np.float32), scores.astype(np.float32), bodyparts


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.data_root) / "keypoints_dlc"
    out_dir.mkdir(parents=True, exist_ok=True)
    vis_dir = Path(args.vis_dir)
    if args.vis > 0:
        vis_dir.mkdir(parents=True, exist_ok=True)

    items = collect_videos(args)
    if args.limit:
        items = items[: args.limit]
    todo = [(v, l) for v, l in items if args.force or not (out_dir / (Path(v).stem + ".npz")).is_file()]
    print(f"[info] 共 {len(items)} 段，待处理 {len(todo)} 段（跳过已完成 {len(items) - len(todo)}）")
    if not todo:
        return 0

    from deeplabcut.modelzoo.video_inference import video_inference_superanimal

    stats = {"ok": 0, "failed": [], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    n_vis = 0
    for ci in range(0, len(todo), args.chunk):
        chunk = todo[ci : ci + args.chunk]
        videos = [v for v, _ in chunk]
        label_of = {v: l for v, l in chunk}
        create_vis = n_vis < args.vis
        print(f"[chunk {ci // args.chunk}] {len(videos)} 段视频推理中…", flush=True)
        try:
            results = video_inference_superanimal(
                videos,
                SUPERANIMAL_NAME,
                MODEL_NAME,
                detector_name=DETECTOR_NAME,
                dest_folder=str(vis_dir) if create_vis else None,
                create_labeled_video=create_vis,
                plot_bboxes=create_vis,
                max_individuals=args.max_individuals,
                batch_size=args.batch_size,
                detector_batch_size=args.detector_batch_size,
                device=args.device,
            )
        except Exception as e:  # noqa: BLE001 - 整 chunk 失败要记录后继续
            print(f"[error] chunk 推理失败: {e}", flush=True)
            stats["failed"].extend(videos)
            continue

        for video in videos:
            stem = Path(video).stem
            try:
                payload = results[video] if isinstance(results, dict) else results.get(video)
                df = payload["df_2d"] if isinstance(payload, dict) and "df_2d" in payload else payload
                keypoint, scores, bodyparts = df_to_arrays(df, args.max_individuals)
                np.savez_compressed(
                    out_dir / f"{stem}.npz",
                    keypoint=keypoint,
                    keypoint_score=scores,
                    bodyparts=np.array(bodyparts),
                    label=np.int64(label_of[video]),
                    video=np.array(str(Path(video).relative_to(Path(args.data_root).resolve()))
                                   if str(video).startswith(str(Path(args.data_root).resolve()))
                                   else str(video)),
                )
                stats["ok"] += 1
                stats.setdefault("videos", {})[stem] = {
                    "frames": int(keypoint.shape[0]),
                    "det_rate": round(float((scores.max(axis=1) > 0.1).mean()), 3),
                    "mean_conf": round(float(scores.mean()), 3),
                }
            except Exception as e:  # noqa: BLE001
                print(f"[error] 转换失败 {stem}: {e}", flush=True)
                stats["failed"].append(video)
        n_vis += len(videos)

        # 每 chunk 落盘一次统计
        stats["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(out_dir / "_summary.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"[progress] 完成 {stats['ok']}/{len(todo)}", flush=True)

    print(f"[done] ok={stats['ok']} failed={len(stats['failed'])} -> {out_dir}")
    return 0 if not stats["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
