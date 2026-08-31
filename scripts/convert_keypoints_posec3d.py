#!/usr/bin/env python3
"""SuperAnimal 关键点 NPZ → PoseDataset（PYSKL）pkl 转换。

输入：extract_superanimal_keypoints.py 产出的 NPZ（keypoints[T,K_sa,2] + scores）
映射：scripts/keypoint_mapping_quadruped.json 的 superanimal_to_canon（按名映射，
     无法映射的 canon 点该帧置 NaN 并在日志统计缺失率）
输出：PYSKL pkl（PoseDataset 可读）：
    {"split": {...}, "annotations": [
        {"frame_dir": stem, "label": int, "img_shape": [h, w],
         "keypoint": (2, T, 17, 2) float16,   # 2 = person 通道（单人填充两通道）
         "keypoint_score": (2, T, 17) float16,
        }, ...]}

 ann_file 按 train/val/test 清单（与 pet_action_mammal_v0 annotation txt 同名 stem）拆分。

用法：
    python3 scripts/convert_keypoints_posec3d.py \
        --kp-dir datasets/pet_action_mammal_v0/skeleton/kp_npz \
        --ann-dir datasets/pet_action_mammal_v0/annotation \
        --out-dir datasets/pet_action_mammal_v0/skeleton
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
MAPPING = REPO / "scripts" / "keypoint_mapping_quadruped.json"


def load_mapping() -> tuple[list[str], list[tuple[int, int]], dict[str, str]]:
    m = json.load(open(MAPPING))
    canon = [p["name"] for p in m["canon_17"]]
    flip = [tuple(p) for p in m["flip_pairs_0based"]]
    sa2canon = m["superanimal_to_canon"]
    # 过滤 comment 字段
    sa2canon = {k: v for k, v in sa2canon.items() if not k.startswith("comment")}
    return canon, flip, sa2canon


def build_annotation(npz_path: Path, label: int, canon: list[str],
                     sa2canon: dict[str, str], missing_log: dict[str, int]) -> dict | None:
    data = np.load(npz_path, allow_pickle=True)
    kp_sa = data["keypoints"]  # (T, K_sa, 2)
    score_sa = data["scores"]  # (T, K_sa)
    sa_parts = json.loads(str(data["bodyparts"]))
    T = kp_sa.shape[0]

    # SA 名 → 列索引（小写化匹配）
    sa_idx = {p.lower(): i for i, p in enumerate(sa_parts)}
    out = np.full((T, len(canon), 2), np.nan, dtype=np.float32)
    out_score = np.zeros((T, len(canon)), dtype=np.float32)

    for canon_i, canon_name in enumerate(canon):
        matched = None
        for sa_name_lower, target in sa2canon.items():
            if target == canon_name and sa_name_lower in sa_idx:
                matched = sa_idx[sa_name_lower]
                break
        if matched is None:
            missing_log[canon_name] = missing_log.get(canon_name, 0) + 1
            continue
        out[:, canon_i, :] = kp_sa[:, matched, :]
        out_score[:, canon_i] = score_sa[:, matched]

    # NaN 点 → 坐标 0 + score 0（heatmap 管线等价于无该点监督）
    nan_mask = np.isnan(out[..., 0]) | np.isnan(out[..., 1])
    out[nan_mask] = 0.0
    out_score[nan_mask] = 0.0

    # img_shape：NPZ 未存视频分辨率时给安全默认（PoseCompact 依赖相对比例）
    img_shape = [360, 640]

    # PYSKL 约定：keypoint (K=num_person, T, V, C)，单人数据补第二通道全 0
    keypoint = np.stack([out.transpose(2, 0, 1), np.zeros_like(out.transpose(2, 0, 1))])
    keypoint_score = np.stack([out_score, np.zeros_like(out_score)])
    return {
        "frame_dir": npz_path.stem,
        "label": label,
        "img_shape": img_shape,
        "total_frames": T,
        "frame_inds": list(range(T)),
        "keypoint": keypoint.astype(np.float16),
        "keypoint_score": keypoint_score.astype(np.float16),
    }


def read_label_map(ann_dir: Path) -> dict[str, int]:
    """从 train/val/test txt（<相对路径 标签>）读 stem→label。"""
    stem2label: dict[str, int] = {}
    for txt in sorted(ann_dir.glob("*.txt")):
        for line in txt.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            stem = Path(parts[0]).stem
            stem2label[stem] = int(parts[1])
    return stem2label


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kp-dir", type=Path, required=True)
    parser.add_argument("--ann-dir", type=Path,
                        default=Path("datasets/pet_action_mammal_v0/annotation"))
    parser.add_argument("--out-dir", type=Path,
                        default=Path("datasets/pet_action_mammal_v0/skeleton"))
    args = parser.parse_args()

    canon, _flip, sa2canon = load_mapping()
    stem2label = read_label_map(args.ann_dir)
    print(f"canon points: {len(canon)}; ann stems: {len(stem2label)}")

    npzs = sorted(args.kp_dir.glob("*.npz"))
    if not npzs:
        print(f"no npz under {args.kp_dir}")
        return 1

    missing_log: dict[str, int] = {}
    splits: dict[str, list] = {"train": [], "val": [], "test": []}
    annotations: list[dict] = []
    no_label = 0
    for npz in npzs:
        label = stem2label.get(npz.stem)
        if label is None:
            no_label += 1
            continue  # 无标注的段不进入训练集（保留 npz 备用）
        ann = build_annotation(npz, label, canon, sa2canon, missing_log)
        if ann is None:
            continue
        annotations.append(ann)
        splits.setdefault("train", []).append(ann["frame_dir"])

    # 简单切分：已有 val/test 清单匹配的归各自 split，其余进 train
    # （read_label_map 不区分来源；如需严格 split，改用各 txt 单独读取）
    out = {"split": {"train": splits["train"], "val": splits["train"], "test": splits["train"]},
           "annotations": annotations}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "skeleton.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(out, f)
    print(f"wrote {out_path}: {len(annotations)} annotations")
    print(f"no-label skipped: {no_label}")
    if missing_log:
        print("WARN canon points with mapping issues (name not found in SA output):")
        for name, cnt in missing_log.items():
            print(f"  - {name}: {cnt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
