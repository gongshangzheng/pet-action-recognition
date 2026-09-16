#!/usr/bin/env python3
"""SuperAnimal-Quadruped 零样本关键点提取（DeepLabCut 生态，远端 GPU 执行）。

对输入视频目录/文件逐个提取关键点，输出 NPZ：
    <out_dir>/<video_stem>.npz   # keypoints [T,K,2] float32, scores [T,K] float32, meta json

幂等：输出已存在则跳过（--force 重算）。

用法：
    # 列出模型实际输出的关键点名（首次必做，用于核对 keypoint_mapping_quadruped.json）
    python3 scripts/extract_superanimal_keypoints.py --list-points

    # 提取
    python3 scripts/extract_superanimal_keypoints.py \
        --input datasets/pet_action_mammal_v0/videos \
        --out datasets/pet_action_mammal_v0/skeleton/kp_npz \
        --destproject /tmp/sa_project

依赖（远端 pet 已具备）：deeplabcut（含 SuperAnimal 模型 zoo 权重）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _list_points() -> int:
    import deeplabcut

    # SuperAnimal-Quadruped 的身体点定义
    cfg = deeplabcut.ModelzooUtils.get_superanimal_quadruped_topview_project  # noqa: F401
    # 直接打印模型身体点定义（不同 DLC 版本 API 有差异，做兼容打印）
    try:
        from deeplabcut.modelzoo.utils import get_superanimal_quadruped_bodyparts  # type: ignore
        parts = get_superanimal_quadruped_bodyparts()
    except Exception:
        try:
            from deeplabcut import ModelzooUtils  # type: ignore
            parts = ModelzooUtils.SUPERANIMAL_QUADRUPED_BODYPOINTS  # type: ignore[attr-defined]
        except Exception:
            parts = None
    if parts is None:
        print("无法直接读取身体点定义；请跑一次小样本推理并查看输出 h5 的列名。")
        return 1
    print("SuperAnimal-Quadruped bodyparts:")
    for i, p in enumerate(parts):
        print(f"  {i}: {p}")
    return 0


def _iter_videos(inp: Path):
    if inp.is_file():
        yield inp
        return
    for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
        yield from sorted(inp.rglob(ext))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="视频目录或单个视频文件")
    parser.add_argument("--out", type=Path, default=Path("datasets/pet_action_mammal_v0/skeleton/kp_npz"))
    parser.add_argument("--destproject", type=Path, default=Path("/tmp/sa_project"),
                        help="DLC modelzoo 推理工作目录")
    parser.add_argument("--force", action="store_true", help="覆盖已有输出")
    parser.add_argument("--list-points", action="store_true", help="打印模型关键点定义后退出")
    parser.add_argument("--video-type", default="mp4")
    args = parser.parse_args()

    if args.list_points:
        return _list_points()
    if not args.input:
        parser.error("--input 或 --list-points 必填其一")

    import numpy as np
    import deeplabcut

    args.out.mkdir(parents=True, exist_ok=True)
    videos = [str(v) for v in _iter_videos(args.input)]
    if not videos:
        print(f"no videos under {args.input}")
        return 1
    print(f"{len(videos)} videos to process")

    # Modelzoo 推理：SuperAnimal-Quadruped 零样本（无项目训练）
    # 不同 DLC 版本 API 名称略有差异，按 2.x 优先。
    video_creator = deeplabcut.ModelzooUtils.VideoAnalysisMethod  # type: ignore[attr-defined]
    deeplabcut.video_inference_superanimal(
        videos=videos,
        superanimal_name="superanimal_quadruped",
        videotype=args.video_type,
        destproject=str(args.destproject),
        video_adapt=False,
        video_creator=video_creator.topview,
        tracking_method="ellipse",
    )

    # DLC 输出为 <video>_supermodel_elastic.h5（或类似后缀），汇总为 NPZ
    import pandas as pd

    n_ok = n_skip = n_fail = 0
    for v in videos:
        stem = Path(v).stem
        out_npz = args.out / f"{stem}.npz"
        if out_npz.exists() and not args.force:
            n_skip += 1
            continue
        h5s = sorted(args.destproject.rglob(f"{stem}*.h5")) or sorted(Path(v).rglob(f"{stem}*.h5"))
        if not h5s:
            print(f"  WARN no h5 for {stem}")
            n_fail += 1
            continue
        df = pd.read_hdf(h5s[0])
        # MultiIndex: (scorer, bodypart, coords)；x/y 与 likelihood
        parts = list(df.columns.get_level_values("bodyparts").unique())
        T = len(df)
        K = len(parts)
        kp = np.zeros((T, K, 2), dtype=np.float32)
        score = np.zeros((T, K), dtype=np.float32)
        for i, part in enumerate(parts):
            kp[:, i, 0] = df[(df.columns.get_level_values("bodyparts") == part)
                             & (df.columns.get_level_values("coords") == "x")].to_numpy().ravel()
            kp[:, i, 1] = df[(df.columns.get_level_values("bodyparts") == part)
                             & (df.columns.get_level_values("coords") == "y")].to_numpy().ravel()
            score[:, i] = df[(df.columns.get_level_values("bodyparts") == part)
                             & (df.columns.get_level_values("coords") == "likelihood")].to_numpy().ravel()
        np.savez(
            out_npz,
            keypoints=kp,
            scores=score,
            bodyparts=json.dumps(parts),
            source_video=str(v),
        )
        n_ok += 1
        print(f"  ok {stem}: T={T} K={K}")

    print(f"=== Extract Complete === ok={n_ok}, skip={n_skip}, fail={n_fail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
