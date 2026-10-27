#!/usr/bin/env python3
"""构建在场门控（presence gate）的帧级数据集：分层抽样 → 1 fps 抽帧 → 昼夜判据 → manifest。

设计依据见 openspec/changes/presence-gate-model/design.md D10：
- 模型是**逐帧图像模型**，因此数据集是「单帧 + 帧级标签」；抽帧必须输出**整帧**（不得用 followcam 裁剪帧）。
- 昼夜以**画面内容**为准：HSV 饱和度均值 S < 20 ≈ 红外灰度段（沿用 datasets skill 的既有裁定），
  文件名时间戳只作辅助元数据，不单独作判据。
- 划分按**日期隔离**（同一天不跨 split），日期 → split 的映射落盘可复现。

只做「帧 + 元数据」，不做 presence 标注（那是 label 阶段的事）。产物：

  <out>/
  ├── frames/<date>/<video_stem>_f000123.jpg   # 整帧 JPEG（长边 1280, q90）
  ├── manifest.csv                            # 每帧一行（含 sat/luma/domain/split）
  ├── splits_by_date.json                     # 日期 → split + 抽样种子
  ├── sample_stats.json                       # 抽样与解码统计
  └── dataset_card.md                         # 人读卡（规模/分布/偏差/口径）

用法（服务器 plf 环境）：
  # 只统计不落盘（先看口径）
  ~/miniconda3/envs/plf/bin/python .claude/skills/datasets/scripts/prepare_gate_frames.py \
      --root ~/pet-final/datasets/cat_raw --out ~/pet-action-recognition/results/gate/dataset_v1 \
      --videos 600 --dry-run

  # 小样本试跑
  ... --videos 600 --pilot 20

  # 全量
  ... --videos 600
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 文件名有三种形态（实测 2,737 段）：
#   <serial>_<house>__event_YYYYMMDD_HHMMSS.mp4                       （309 段，带设备前缀）
#   <serial>_<house>__event_YYYYMMDD_HHMMSS__src_<hash>.mp4           （83 段，带设备前缀 + 来源标记）
#   event_YYYYMMDD_HHMMSS.mp4                                        （2,345 段，无前缀）
DATETIME_PATTERN = re.compile(r"event_(?P<date>\d{8})_(?P<time>\d{6})")
PREFIX_PATTERN = re.compile(r"^(?P<serial>\d+)_(?P<house>[a-z0-9]+)__")
UPLOAD_PATTERN = re.compile(r"/upload/(?P<bucket>\d+)/")
SAT_IR_THRESHOLD = 20.0          # S < 20 → 红外灰度段（datasets skill 口径）
DEFAULT_LONG_SIDE = 1280
DEFAULT_JPEG_QUALITY = 90
SPLIT_RATIO = (0.70, 0.15, 0.15)


def load_upload_buckets(root: Path) -> dict[str, str]:
    """从 annotations/path_mapping.csv 取「视频 → 原始 /upload/<bucket>/ 桶」（户/项目代理键）。"""
    mapping_file = root / "annotations" / "path_mapping.csv"
    if not mapping_file.is_file():
        return {}
    buckets: dict[str, str] = {}
    with mapping_file.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            original = row.get("original_video") or ""
            match = UPLOAD_PATTERN.search(original)
            if match:
                buckets[Path(row["video"]).name] = f"upload{match.group('bucket')}"
    return buckets


def parse_name(path: Path, upload_buckets: dict[str, str]) -> dict | None:
    """解析日期/小时，以及尽力而为的「设备 + 分组」键（前缀优先，其次 annotations 里的 upload 桶）。"""
    match = DATETIME_PATTERN.search(path.name)
    if not match:
        return None
    entry = {
        "date": match.group("date"),
        "hour": int(match.group("time")[:2]),
        "serial": "",
        "household": "",
        "group": "",
    }
    prefix = PREFIX_PATTERN.match(path.name)
    if prefix:
        entry["serial"] = prefix.group("serial")
        entry["household"] = prefix.group("house")
        entry["group"] = prefix.group("house")
    bucket = upload_buckets.get(path.name)
    if bucket:
        entry["group"] = bucket
        entry["household"] = entry["household"] or bucket
    if not entry["group"]:
        entry["group"] = "unknown"
        entry["household"] = "unknown"
    return entry


def list_videos(root: Path) -> list[Path]:
    return sorted((root / "videos").glob("*.mp4"))


def stratified_select(entries: list[dict], target: int, seed: int, pilot: int | None) -> list[dict]:
    """按日期分层 + 户码/小时多样性挑选；同日内轮转不同户码。"""
    rng = random.Random(seed)
    by_date: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        by_date[entry["date"]].append(entry)

    dates = sorted(by_date)
    rng.shuffle(dates)
    for date in dates:
        rng.shuffle(by_date[date])
        by_date[date].sort(key=lambda e: (e["household"], e["hour"]))  # 稳定后仍保多样
        rng.shuffle(by_date[date])

    wanted = pilot if pilot else target
    picked: list[dict] = []
    per_date: Counter[str] = Counter()
    while len(picked) < wanted and len(picked) < len(entries):
        progressed = False
        for date in dates:
            if len(picked) >= wanted:
                break
            pool = by_date[date]
            if per_date[date] >= len(pool):
                continue
            picked.append(pool[per_date[date]])
            per_date[date] += 1
            progressed = True
        if not progressed:
            break
    return picked


def assign_splits(dates: list[str], seed: int) -> dict[str, str]:
    """日期 → split；按 70/15/15 切分（确定性：种子 + 排序后的日期）。"""
    ordered = sorted(dates)
    random.Random(seed).shuffle(ordered)
    total = len(ordered)
    n_train = max(1, round(total * SPLIT_RATIO[0]))
    n_val = max(1, round(total * SPLIT_RATIO[1]))
    mapping: dict[str, str] = {}
    for index, date in enumerate(ordered):
        mapping[date] = "train" if index < n_train else ("val" if index < n_train + n_val else "test")
    return mapping


def frame_indices(total: int, fps: float) -> list[int]:
    """1 fps 采样：每 round(fps) 帧取一帧；不足 1 秒的短视频取首帧。"""
    step = max(1, round(fps))
    indices = list(range(0, total, step))
    return indices or [0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, required=True, help="cat_raw 目录（含 videos/ 与 annotations/）")
    parser.add_argument("--out", type=Path, required=True, help="产物目录（如 results/gate/dataset_v1）")
    parser.add_argument("--videos", type=int, default=600, help="目标抽样视频数（默认 600）")
    parser.add_argument("--pilot", type=int, default=None, help="小样本试跑：只处理前 N 段")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--long-side", type=int, default=DEFAULT_LONG_SIDE)
    parser.add_argument("--jpeg-quality", type=int, default=DEFAULT_JPEG_QUALITY)
    parser.add_argument("--dry-run", action="store_true", help="只做抽样统计，不解码不落盘")
    args = parser.parse_args()

    videos = list_videos(args.root)
    if not videos:
        print(f"[prepare_gate_frames] 找不到视频：{args.root}/videos", file=sys.stderr)
        return 2

    upload_buckets = load_upload_buckets(args.root)
    entries, unparsed = [], []
    for path in videos:
        meta = parse_name(path, upload_buckets)
        if meta is None:
            unparsed.append(path.name)
            continue
        entries.append({"path": path, **meta})

    picked = stratified_select(entries, args.videos, args.seed, args.pilot)
    split_map = assign_splits(sorted({e["date"] for e in entries}), args.seed)

    print(f"[prepare_gate_frames] 视频总数 {len(videos)}（可解析 {len(entries)}，未解析 {len(unparsed)}）")
    print(f"[prepare_gate_frames] 抽样 {len(picked)} 段，覆盖日期 {len({e['date'] for e in picked})} 天，"
          f"分组 {dict(Counter(e['group'] for e in picked).most_common(8))}")
    coverage = Counter("prefix" if e["serial"] else ("upload_bucket" if e["group"].startswith("upload") else "unknown")
                       for e in entries)
    print(f"[prepare_gate_frames] 设备信息覆盖（全量）：{dict(coverage)}")
    print(f"[prepare_gate_frames] 日期→split：train {sum(1 for v in split_map.values() if v=='train')} / "
          f"val {sum(1 for v in split_map.values() if v=='val')} / test {sum(1 for v in split_map.values() if v=='test')}")
    if args.dry_run:
        hours = Counter(e["hour"] for e in picked)
        print(f"[prepare_gate_frames] 抽样小时分布：{dict(sorted(hours.items()))}")
        print("[prepare_gate_frames] --dry-run：未解码、未落盘")
        return 0

    import cv2
    import decord

    frames_dir = args.out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    errors: list[str] = []
    sat_by_domain: dict[str, list[float]] = defaultdict(list)
    frame_count = 0

    for order, entry in enumerate(picked, 1):
        path: Path = entry["path"]
        stem = path.stem
        split = split_map.get(entry["date"], "train")
        try:
            reader = decord.VideoReader(str(path), num_threads=2)
            fps = float(reader.get_avg_fps()) or 15.0
            total = len(reader)
            indices = frame_indices(total, fps)
            batch = reader.get_batch(indices).asnumpy()
        except Exception as error:  # 解码失败不中断整批
            errors.append(f"{path.name}: {type(error).__name__}: {error}")
            continue

        out_dir = frames_dir / entry["date"]
        out_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in zip(indices, batch):
            height, width = frame.shape[:2]
            scale = args.long_side / max(height, width)
            if scale < 1.0:
                frame = cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            sat = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)[..., 1]
            sat_mean, luma_mean = float(sat.mean()), float(gray.mean())
            domain = "night" if sat_mean < SAT_IR_THRESHOLD else "day"
            sat_by_domain[domain].append(sat_mean)
            file_path = out_dir / f"{stem}_f{index:06d}.jpg"
            cv2.imwrite(str(file_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
            rows.append({
                "path": str(file_path.relative_to(args.out)),
                "video": path.name,
                "serial": entry["serial"],
                "household": entry["household"],
                "group": entry["group"],
                "date": entry["date"],
                "hour": entry["hour"],
                "frame_idx": index,
                "ts_sec": round(index / fps, 3),
                "width": frame.shape[1],
                "height": frame.shape[0],
                "sat_mean": round(sat_mean, 2),
                "luma_mean": round(luma_mean, 1),
                "domain": domain,
                "split": split,
            })
            frame_count += 1
        if order % 25 == 0 or order == len(picked):
            print(f"[prepare_gate_frames] {order}/{len(picked)} 段，累计 {frame_count} 帧；失败 {len(errors)} 段")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = args.out / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()) if rows else ["path"])
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "splits_by_date.json").write_text(
        json.dumps({"seed": args.seed, "ratio": SPLIT_RATIO, "splits": split_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    stats = {
        "source_root": str(args.root),
        "videos_total": len(videos),
        "videos_unparsed": unparsed[:20],
        "videos_selected": len(picked),
        "videos_decoded": len(picked) - len(errors),
        "frames": frame_count,
        "decode_errors": errors,
        "seed": args.seed,
        "sat_ir_threshold": SAT_IR_THRESHOLD,
        "domain_frames": dict(Counter(row["domain"] for row in rows)),
        "split_frames": dict(Counter(row["split"] for row in rows)),
        "household_frames": dict(Counter(row["household"] for row in rows)),
        "group_frames": dict(Counter(row["group"] for row in rows)),
        "date_frames": dict(sorted(Counter(row["date"] for row in rows).items())),
        "sat_median_by_domain": {k: round(sorted(v)[len(v) // 2], 2) for k, v in sat_by_domain.items() if v},
        "fps_sampling": "1 frame per round(fps) frames",
        "long_side": args.long_side,
        "jpeg_quality": args.jpeg_quality,
        "note": "presence 标签尚未生成：本脚本只产出帧与元数据",
    }
    (args.out / "sample_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    card = [
        "# 门控数据集 card（dataset_v1）",
        "",
        f"- 源目录：`{args.root}`（cat_raw）",
        f"- 抽样：{len(picked)}/{len(videos)} 段，种子 {args.seed}；解码失败 {len(errors)} 段",
        f"- 抽帧：1 fps（每 {int(round(15))} 帧取 1）；整帧 JPEG 长边 {args.long_side}、q{args.jpeg_quality}",
        f"- 帧数：{frame_count}（domain {stats['domain_frames']}；split {stats['split_frames']}）",
        f"- 昼夜判据：HSV 饱和度均值 S < {SAT_IR_THRESHOLD} → night；各域饱和度中位 {stats['sat_median_by_domain']}",
        f"- 划分：按日期隔离 70/15/15（见 `splits_by_date.json`）",
        "- **未包含**：presence 标签（待 label 阶段）、负样本核验（待人工）",
        "- 已知偏差：全部来自同一批设备（8+ 户码）；行为区间标注只覆盖部分时段。",
        "",
    ]
    (args.out / "dataset_card.md").write_text("\n".join(card), encoding="utf-8")

    print(f"[prepare_gate_frames] 完成：{frame_count} 帧 → {args.out}")
    print(f"[prepare_gate_frames] 域分布 {stats['domain_frames']}｜split {stats['split_frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
