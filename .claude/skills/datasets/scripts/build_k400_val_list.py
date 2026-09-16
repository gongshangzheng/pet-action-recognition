"""构建 K400 val 评测用 list：解压 val 分片 + 扫 mp4 + 查 validate.csv/label_map → val_list.txt。

产物（~/mnt/kinetics400/）：
- videos_val/   解压出的 mp4（扁平 {youtube_id}_{start}_{end}.mp4）
- kinetics400_val_list_videos.txt   每行 "<相对路径> <类id>"，匹配 mmaction2 VideoDataset

mmaction2 VideoDataset ann_file 格式：每行 "rel_video_path label_id"。
"""
from __future__ import annotations

import csv
import os
import sys
import tarfile
from pathlib import Path

ROOT = Path(os.path.expanduser("~/mnt/kinetics400"))
PARTS_DIR = ROOT / "val_parts"
VIDEOS_DIR = ROOT / "videos_val"
ANNO = ROOT / "annotations" / "kinetics400" / "validate.csv"
LABEL_MAP = ROOT / "annotations" / "label_map_k400.txt"
OUT_LIST = ROOT / "kinetics400_val_list_videos.txt"


def load_label_map() -> dict[str, int]:
    """class_name → id（行号 0-based）。"""
    out = {}
    with open(LABEL_MAP) as f:
        for i, ln in enumerate(f):
            name = ln.strip()
            if name:
                out[name] = i
    return out


def load_validate() -> dict[tuple[str, int, int], str]:
    """(youtube_id, start, end) → class_name。"""
    out = {}
    with open(ANNO, newline="") as f:
        for row in csv.DictReader(f):
            try:
                yt = row["youtube_id"].strip()
                s = int(float(row["time_start"]))
                e = int(float(row["time_end"]))
            except (KeyError, ValueError):
                continue
            out[(yt, s, e)] = row["label"].strip()
    return out


def parse_fname(fn: str) -> tuple[str, int, int] | None:
    """{youtube_id}_{start:06d}_{end:06d}.mp4 → (youtube_id, start, end)。
    youtube_id 可能含下划线，故取最后两个 _NNNNNN 段为 start/end。"""
    if not fn.endswith(".mp4"):
        return None
    stem = fn[:-4]
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    try:
        e = int(parts[-1])
        s = int(parts[-2])
    except ValueError:
        return None
    yt = "_".join(parts[:-2])
    return yt, s, e


def extract_all() -> int:
    """解压所有 part_*.tar.gz → videos_val/，返回解压出的 mp4 数。"""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    parts = sorted(PARTS_DIR.glob("part_*.tar.gz"))
    print(f"[extract] {len(parts)} 分片 → {VIDEOS_DIR}", flush=True)
    for i, p in enumerate(parts):
        with tarfile.open(p, "r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name.endswith(".mp4"):
                    # 扁平提取（去掉 ./ 前缀和目录层级）
                    member.name = os.path.basename(member.name)
                    tf.extract(member, VIDEOS_DIR)
                    n += 1
        print(f"  part {i+1}/{len(parts)} done, 累计 {n} mp4", flush=True)
    return n


def build_list(label_map: dict[str, int], validate: dict) -> int:
    """扫 videos_val/ → 写 val_list。返回写入条数（+ 未匹配数）。"""
    n_ok = n_miss = 0
    with open(OUT_LIST, "w") as fout:
        for fn in sorted(os.listdir(VIDEOS_DIR)):
            key = parse_fname(fn)
            if not key:
                continue
            label_name = validate.get(key)
            if label_name is None or label_name not in label_map:
                n_miss += 1
                continue
            cid = label_map[label_name]
            fout.write(f"{fn} {cid}\n")
            n_ok += 1
    print(f"[list] 写 {n_ok} 条到 {OUT_LIST}（未匹配 {n_miss}）", flush=True)
    return n_ok


def main() -> int:
    label_map = load_label_map()
    validate = load_validate()
    print(f"[load] label_map {len(label_map)} 类, validate {len(validate)} 条", flush=True)
    if not any(VIDEOS_DIR.glob("*.mp4")):
        extract_all()
    build_list(label_map, validate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
