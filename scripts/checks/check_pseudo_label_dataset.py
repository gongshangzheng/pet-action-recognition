#!/usr/bin/env python3
"""伪标签数据集自检（gdino-distill-yolo-detector 1.2 / 1.3）。

输入：导出产物目录（含 dataset.json、labels/、可选 drops.jsonl）。

产出：
  <out>/splits.json    按源视频的划分清单（每 split 的视频数/帧数/框数 + 视频名列表）
  stdout + <out>/selfcheck.json
      - 同视频跨 split 违例数（必须为 0）
      - 类别分布、空标注帧比例、每帧平均实例数
      - 各类过滤的丢弃总量（读 drops.jsonl）
      - 同一事件日跨 split 的视频对数量
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVENT_DAY = re.compile(r"event_(\d{8})_")


def event_day(video: str) -> str | None:
    m = EVENT_DAY.search(video)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, required=True, help="导出产物目录")
    ap.add_argument("--verify-traceability", type=int, default=0, metavar="N",
                    help="随机抽 N 帧，逐框比对「标注文件」与「源缓存该锚点的候选」，验证无插值/无凭空框")
    ap.add_argument("--detections-dir", type=Path, default=None,
                    help="源缓存目录（--verify-traceability 需要）")
    ap.add_argument("--emit-yolo-config", action="store_true",
                    help="同时产出 Ultralytics 训练所需的 data.yaml 与 train/val/test 清单")
    args = ap.parse_args()

    manifest = json.loads((args.dataset / "dataset.json").read_text(encoding="utf-8"))
    records = manifest["records"]

    # ---- 1.2 划分自检 ----
    video_splits: dict[str, set[str]] = defaultdict(set)
    per_split: dict[str, dict] = defaultdict(lambda: {"videos": set(), "frames": 0, "boxes": 0})
    for r in records:
        video_splits[r["video"]].add(r["split"])
        s = per_split[r["split"]]
        s["videos"].add(r["video"])
        s["frames"] += 1
        s["boxes"] += r["n_boxes"]

    violations = {v: sorted(s) for v, s in video_splits.items() if len(s) > 1}
    splits_out = {
        "schema": "pseudo-label-splits-v1",
        "rule": "按源视频稳定哈希划分；同一视频只进一个 split",
        "splits": {k: {"videos": len(v["videos"]), "frames": v["frames"], "boxes": v["boxes"],
                       "video_list": sorted(x.split("/")[-1] for x in v["videos"])}
                   for k, v in sorted(per_split.items())},
        "cross_split_violations": len(violations),
    }
    (args.dataset / "splits.json").write_text(json.dumps(splits_out, ensure_ascii=False, indent=1),
                                              encoding="utf-8")

    # ---- 1.3 数据集自检 ----
    class_counts = Counter()
    empty_frames = 0
    for r in records:
        label_path = args.dataset / r["label"]
        lines = [ln for ln in label_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            empty_frames += 1
        for ln in lines:
            class_counts[int(ln.split()[0])] += 1

    drops = Counter()
    drop_frames = 0
    drops_path = args.dataset / "drops.jsonl"
    if drops_path.is_file():
        for line in drops_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            drop_frames += 1
            for d in row["drops"]:
                drops[d["reason"]] += 1

    day_split: dict[str, set[str]] = defaultdict(set)
    for r in records:
        day = event_day(r["video"])
        if day:
            day_split[day].add(r["split"])
    leaky_days = {d: sorted(s) for d, s in day_split.items() if len(s) > 1}

    classes = manifest["classes"]
    selfcheck = {
        "schema": "pseudo-label-selfcheck-v1",
        "teacher_fingerprint": manifest["teacher_fingerprint"],
        "params": manifest["params"],
        "frames": len(records),
        "boxes": sum(r["n_boxes"] for r in records),
        "boxes_per_frame": round(sum(r["n_boxes"] for r in records) / max(1, len(records)), 3),
        "empty_label_frames": empty_frames,
        "empty_label_ratio": round(empty_frames / max(1, len(records)), 4),
        "class_counts": {classes[k]: v for k, v in sorted(class_counts.items())},
        "drop_frames": drop_frames,
        "drops_by_reason": dict(drops),
        "cross_split_violations": len(violations),
        "same_event_day_cross_split": {"days": len(leaky_days), "detail": leaky_days},
        "image_wh_sample": records[0]["image_wh"] if records else None,
    }
    (args.dataset / "selfcheck.json").write_text(json.dumps(selfcheck, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    print(json.dumps({k: v for k, v in selfcheck.items()
                      if k not in ("params", "same_event_day_cross_split")}, ensure_ascii=False))
    print(f"同事件日跨 split：{len(leaky_days)} 天")
    if args.verify_traceability:
        if args.detections_dir is None:
            raise ValueError("--verify-traceability 需要 --detections-dir")
        from scripts.export_pseudo_labels import filter_candidates
        import random
        rng = random.Random(manifest["params"]["seed"])
        sample = rng.sample(records, min(args.verify_traceability, len(records)))
        bad = 0
        for r in sample:
            cache = json.loads((args.detections_dir / r["detection_cache"]).read_text(encoding="utf-8"))
            state = cache["anchors"][str(r["frame"])]
            kept, _ = filter_candidates(state)
            src = sorted(tuple(round(v, 2) for v in c["box"]) for c in kept)
            w, h = r["source_wh"]
            got = []
            for line in (args.dataset / r["label"]).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                _, cx, cy, bw, bh = (float(x) for x in line.split())
                got.append((round((cx - bw / 2) * w, 2), round((cy - bh / 2) * h, 2),
                            round((cx + bw / 2) * w, 2), round((cy + bh / 2) * h, 2)))
            got.sort()
            if got != src:
                bad += 1
                print(f"  MISMATCH {r['image']}: label={got} cache={src}")
        print(f"[traceability] 抽 {len(sample)} 帧，逐框与源缓存不一致 {bad} 帧"
              f"（0 = 标注完全来自该锚点候选，无插值、无凭空框）")
        if bad:
            return 1

    if args.emit_yolo_config:
        # Ultralytics：图像为扁平目录，用 txt 清单指定各 split
        for split in ("train", "val", "test"):
            # Ultralytics 不按 data.yaml 的 path 解析 txt 里的相对路径，故写绝对路径
            imgs = sorted(str((args.dataset / r["image"]).resolve())
                          for r in records if r["split"] == split)
            (args.dataset / f"{split}.txt").write_text(
                "\n".join(imgs) + "\n", encoding="utf-8")
            print(f"  {split}.txt: {len(imgs)} 张")
        yaml_text = (
            f"path: {args.dataset.resolve()}\n"
            "train: train.txt\n"
            "val: val.txt\n"
            "test: test.txt\n"
            "names:\n"
            + "".join(f"  {i}: {n}\n" for i, n in enumerate(manifest["classes"]))
        )
        (args.dataset / "data.yaml").write_text(yaml_text, encoding="utf-8")
        print(f"data.yaml -> {args.dataset / 'data.yaml'}")

    print(f"SELFCHECK DONE -> {args.dataset}")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
