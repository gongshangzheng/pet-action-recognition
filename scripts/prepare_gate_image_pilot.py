#!/usr/bin/env python3
"""Prepare a deterministic, frame-only image labeling pilot from video manifests."""
import argparse
import csv
import hashlib
import json
import random
import math
from collections import defaultdict
from pathlib import Path


QUOTAS = {"train": 140, "val": 30, "test": 30}


def read_rows(manifest, labels_path=None):
    with open(manifest, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    labels = defaultdict(set)
    if labels_path:
        with open(labels_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if r.get("label") == "absent":
                        labels[(str(r.get("video", "")), str(r.get("frame_idx", "")))].add("absent")
    return rows, labels


def select_sources(rows, seed=20261030, sources=200, labels=None, include_reserves=False):
    """Return split -> source rows; dates never cross splits, caps are exact."""
    labels = labels or {}
    if sources != 200:
        raise ValueError("this frozen pilot requires exactly 200 sources")
    grouped = {}
    for row in rows:
        video = row.get("video", "").strip()
        date = row.get("date", "").strip()
        if video and date:
            grouped.setdefault(video, row)
    if len(grouped) < sources:
        raise ValueError(f"usable source pool has {len(grouped)} distinct videos; need {sources}")
    by_date = defaultdict(list)
    for row in grouped.values():
        by_date[row["date"]].append(row)
    dates = sorted(by_date)
    rng = random.Random(seed)
    rng.shuffle(dates)
    splits = {k: [] for k in QUOTAS}
    # Assign whole dates, then fill exact source quotas. Greedy bounded search avoids
    # splitting dates while preferring the requested 70/15/15 date proportions.
    targets = QUOTAS.copy()
    order = ("train", "val", "test")
    cursor = 0
    for split in order:
        while len(splits[split]) < targets[split] and cursor < len(dates):
            d = dates[cursor]; cursor += 1
            day_rows = by_date[d].copy()
            rng.shuffle(day_rows)
            splits[split].extend(day_rows)
        if len(splits[split]) < targets[split]:
            raise ValueError(f"date-disjoint split cannot fill {split} quota {targets[split]}")
    # If any date remains unused this is fine; every chosen date belongs to one split.
    result = {}
    for split, items in splits.items():
        neg = [r for r in items if any(v == "absent" for (video, _), vals in labels.items() for v in vals if video == r["video"])]
        rng.shuffle(neg)
        chosen = neg[:len(items)//2]
        chosen_ids = {r["video"] for r in chosen}
        chosen = chosen[:targets[split]//2]
        chosen_ids = {r["video"] for r in chosen}
        buckets = defaultdict(list)
        for row in items:
            if row["video"] not in chosen_ids:
                buckets[(row.get("household", "unknown"), row.get("domain", "unknown"))].append(row)
        keys = sorted(buckets)
        rng.shuffle(keys)
        for bucket in buckets.values():
            rng.shuffle(bucket)
        while len(chosen) < targets[split]:
            for key in keys:
                if buckets[key] and len(chosen) < targets[split]:
                    chosen.append(buckets[key].pop())
        result[split] = chosen
        if include_reserves:
            used = {row['video'] for row in chosen}
            result[split] += [row for row in items if row['video'] not in used]
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True); p.add_argument("--video-root", required=True)
    p.add_argument("--out", required=True); p.add_argument("--sources", type=int, default=200)
    p.add_argument("--seed", type=int, default=20261030); p.add_argument("--labels", help="optional teacher-label JSONL")
    a = p.parse_args()
    import cv2
    cv2.setNumThreads(1)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()): raise SystemExit(f"output directory is not empty: {out}")
    rows, label_rows = read_rows(a.manifest, a.labels)
    selected = select_sources(rows, a.seed, a.sources, label_rows, include_reserves=True)
    root = Path(a.video_root)
    paths = {}
    for f in root.rglob("*"):
        if f.is_file(): paths.setdefault(f.name, []).append(f)
    resolved = {}
    for split, sources in selected.items():
        for row in sources:
            matches = paths.get(row["video"], [])
            if len(matches) != 1:
                raise ValueError(f"source must resolve exactly once: {row['video']} ({len(matches)} matches)")
            resolved[row["video"]] = matches[0]
    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir()
    items, source_rows, errors = [], [], []
    for split, sources in selected.items():
        completed = 0
        for row in sources:
            if completed == QUOTAS[split]:
                break
            video = resolved[row["video"]]
            capture = cv2.VideoCapture(str(video))
            before = len(items)
            written = []
            try:
                if not capture.isOpened():
                    raise RuntimeError(f"cannot open {video}")
                count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = capture.get(cv2.CAP_PROP_FPS)
                if count < 3 or not math.isfinite(fps) or fps <= 0:
                    raise ValueError(f"invalid metadata for {video}: frames={count} fps={fps}")
                identity = hashlib.sha256(row["video"].encode()).hexdigest()[:16]
                for index in (count // 3, 2 * count // 3):
                    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError(f"cannot decode {video} frame {index}")
                    height, width = frame.shape[:2]
                    scale = min(1.0, 1280 / max(width, height))
                    if scale < 1:
                        frame = cv2.resize(frame, (round(width * scale), round(height * scale)))
                    relative = f"frames/{identity}_f{index:08d}.jpg"
                    if not cv2.imwrite(str(out / relative), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                        raise RuntimeError(f"cannot write {relative}")
                    written.append(out / relative)
                    items.append({"path": relative, "file": relative, "video": row["video"],
                                  "source_id": identity, "date": row["date"],
                                  "household": row.get("household", "unknown"), "split": split,
                                  "domain": row.get("domain", "unknown"), "scenario": "pilot",
                                  "frame_idx": index, "ts_sec": index / fps,
                                  "width": frame.shape[1], "height": frame.shape[0],
                                  "native_width": width, "native_height": height,
                                  "teacher_label": ""})
                source_rows.append({**row, "source_path": str(video), "source_id": identity,
                                    "split": split, "duration": count / fps, "fps": fps})
                completed += 1
            except Exception as error:
                del items[before:]
                for file in written:
                    file.unlink()
                errors.append({"video": row["video"], "error": str(error)})
                (out / "selection_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
                print(f"[pilot] rejected {row['video']}: {error}", flush=True)
            finally:
                capture.release()
            print(f"[pilot] {len(source_rows)}/200 videos, {len(items)}/400 images", flush=True)
        if completed != QUOTAS[split]:
            raise RuntimeError(f"exhausted {split} sources: {completed}/{QUOTAS[split]}; see selection_errors.json")
    rng = random.Random(a.seed)
    rng.shuffle(items)
    for name, records in (("source_manifest.csv", source_rows), ("frames.csv", items)):
        with (out / name).open("w", encoding="utf-8", newline="") as stream:
            fields = sorted({key for record in records for key in record})
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
    (out / "selection_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2) + "\n")
    negative_sources = {video for video, _ in label_rows}
    candidate_count = sum(row["video"] in negative_sources for row in source_rows)
    (out / "dataset_card.md").write_text(
        f"# Image pilot\n\nSeed: {a.seed}. 200 sources; 400 whole-frame images.\n"
        "Frames: floor(N/3), floor(2N/3). Split: 280 train / 60 val / 60 test; dates disjoint.\n"
        f"Sources with teacher-absent candidates: {candidate_count}; human labels are not inferred.\n"
        "Source pool: existing manifest only; not a census of all raw videos. Domain metadata inherited from manifest.\n"
        "Labels: present / absent; uncertain means skip and review, not a training class.\n")
    # Publish items last: the review API must not expose a partially extracted set.
    payload = {"count": len(items), "items": items, "mode": "image", "hide_teacher": True,
               "title": "图片标注 · 首轮400张", "description": "先标图片，再训练；只判断画面中有没有宠物。",
               "seed": a.seed}
    (out / "items.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__": main()
