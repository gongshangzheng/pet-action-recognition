#!/usr/bin/env python3
"""Build the seven-class, day-disjoint cat action v1 index without copying videos."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

CLASSES = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]
CLASS_INDEX = {name: index for index, name in enumerate(CLASSES)}
LABEL_MAPPING = {
    "common/activity": "activity",
    "common/eating": "eating",
    "common/drinking": "drinking",
    "common/prolonged_stationary": "prolonged_stationary",
    "common/grooming": "grooming",
    "common/toileting": "toileting",
    "abnormal/scratching": "abnormal",
    "abnormal/gnawing": "abnormal",
    "abnormal/fall": "abnormal",
    "abnormal/seizure": "abnormal",
}
EXCLUDED_LABELS = {
    "common/multi_cat_chase",
    "common/multi_cat_roughplay",
}
MIN_FRAMES = 60
SPLIT_SEED_LIMIT = 10_000
BALANCED_PER_CLASS = 12
TRAIN_MIN = 40
EVAL_MIN = 15
TOILETING_TRAIN_MIN = 10
TOILETING_EVAL_MIN = 4
FRAME_NUMBERING = "1-based inclusive"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_key(sample_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}|{sample_id}".encode("utf-8")).hexdigest()


def event_day(video: str) -> str:
    match = re.search(r"event_(20\d{6})_", Path(video).name)
    return match.group(1) if match else f"video:{video}"


def map_label(label: str) -> str | None:
    return LABEL_MAPPING.get(label)


def read_source(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def build_candidates(
    rows: list[dict],
    min_frames: int = MIN_FRAMES,
) -> tuple[list[dict], Counter, Counter, dict[str, int]]:
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_video[row["video"]].append(row)

    filter_counts: Counter = Counter()
    excluded_counts: Counter = Counter()
    class_counts: Counter = Counter()
    candidates: list[dict] = []
    for video, video_rows in by_video.items():
        day = event_day(video)
        for row in video_rows:
            source_label = row["label"]
            if source_label in EXCLUDED_LABELS:
                filter_counts["excluded_label"] += 1
                excluded_counts[source_label] += 1
                continue
            class_name = map_label(source_label)
            if class_name is None:
                raise ValueError(f"Unmapped source label: {source_label}")
            start = int(row["start_frame"])
            end = int(row["end_frame"])
            if end - start + 1 < min_frames:
                filter_counts["too_short"] += 1
                continue
            overlapping = any(
                other is not row
                and max(start, int(other["start_frame"]))
                <= min(end, int(other["end_frame"]))
                for other in video_rows
            )
            if overlapping:
                filter_counts["overlapping"] += 1
                continue
            sample_id = hashlib.sha256(
                f"{video}|{row['task_id']}|{start}|{end}|{source_label}".encode("utf-8")
            ).hexdigest()[:20]
            candidates.append(
                {
                    "video": video,
                    "task_id": int(row["task_id"]),
                    "start_frame": start,
                    "end_frame": end,
                    "label": CLASS_INDEX[class_name],
                    "label_name": class_name,
                    "source_label": source_label,
                    "day": day,
                    "sample_id": sample_id,
                }
            )
            class_counts[class_name] += 1
    return candidates, filter_counts, excluded_counts, dict(class_counts)


def find_split(
    candidates: list[dict],
    seed_limit: int = SPLIT_SEED_LIMIT,
    train_min: int = TRAIN_MIN,
    eval_min: int = EVAL_MIN,
    toileting_train_min: int = TOILETING_TRAIN_MIN,
    toileting_eval_min: int = TOILETING_EVAL_MIN,
) -> tuple[dict[str, set[str]], int]:
    days = sorted({row["day"] for row in candidates})
    fifth = len(days) // 5
    if fifth < 2:
        raise RuntimeError(f"Not enough event days for a day-disjoint split: {len(days)}")
    for seed in range(seed_limit):
        shuffled = days.copy()
        random.Random(seed).shuffle(shuffled)
        groups = {
            "val": set(shuffled[:fifth]),
            "test": set(shuffled[fifth : 2 * fifth]),
            "train": set(shuffled[2 * fifth :]),
        }
        counts = {
            split: Counter(
                row["label_name"] for row in candidates if row["day"] in group
            )
            for split, group in groups.items()
        }
        ok = True
        for split in ("train", "val", "test"):
            for name in CLASSES:
                minimum = train_min if split == "train" else eval_min
                if name == "toileting":
                    minimum = (
                        toileting_train_min
                        if split == "train"
                        else toileting_eval_min
                    )
                if counts[split][name] < minimum:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return groups, seed
    raise RuntimeError(
        "No day-disjoint split satisfies the per-class minimums; "
        "inspect the audit and adjust the recorded rule"
    )


def select_balanced(rows: list[dict], seed: int) -> list[dict]:
    selected: list[dict] = []
    for label in range(len(CLASSES)):
        pool = sorted(
            (row for row in rows if row["label"] == label),
            key=lambda row: stable_key(row["sample_id"], seed),
        )
        selected.extend(pool[:BALANCED_PER_CLASS])
    return sorted(selected, key=lambda row: stable_key(row["sample_id"], seed))


def jsonl_text(rows: list[dict]) -> str:
    keys = ("video", "task_id", "start_frame", "end_frame", "label", "sample_id")
    return "".join(
        json.dumps({key: row[key] for key in keys}, ensure_ascii=False) + "\n"
        for row in rows
    )


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_if_unchanged(path: Path, text: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == text:
            return
        if not force:
            raise RuntimeError(f"Existing output differs: {path}")
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def verify_videos(
    candidates: list[dict],
    videos_root: Path,
) -> tuple[list[dict], dict]:
    try:
        from decord import VideoReader
    except Exception as exc:  # pragma: no cover - server-only dependency
        raise RuntimeError("Decord is required for --verify-videos") from exc

    frame_counts: dict[str, int | None] = {}
    invalid = Counter()
    valid: list[dict] = []
    for row in candidates:
        video = row["video"]
        if video not in frame_counts:
            try:
                frame_counts[video] = len(
                    VideoReader(str(videos_root / video), num_threads=1)
                )
            except Exception:
                frame_counts[video] = None
        total = frame_counts[video]
        if total is None:
            invalid["unreadable"] += 1
            continue
        if row["end_frame"] > total:
            invalid["out_of_range"] += 1
            continue
        row["total_frames"] = total
        valid.append(row)
    return valid, {
        "enabled": True,
        "videos_checked": len(frame_counts),
        "invalid": dict(invalid),
        "valid_candidates": len(valid),
    }


def write_outputs(
    root: Path,
    source: Path,
    candidates: list[dict],
    split_groups: dict[str, set[str]],
    split_seed: int,
    filter_counts: Counter,
    excluded_counts: Counter,
    class_counts: dict[str, int],
    video_check: dict,
    force: bool,
) -> dict:
    out_dir = root / "datasets/cat_action_v1"
    audit_path = root / "results/training/cat_action_v1/data_audit.json"
    split_rows: dict[str, list[dict]] = {}
    split_counts: dict[str, dict[str, int]] = {}
    for split in ("train", "val", "test"):
        rows = [
            row for row in candidates if row["day"] in split_groups[split]
        ]
        split_rows[split] = sorted(
            rows, key=lambda row: stable_key(row["sample_id"], split_seed)
        )
        split_counts[split] = dict(Counter(row["label_name"] for row in rows))

    balanced_rows = {
        split: select_balanced(split_rows[split], split_seed)
        for split in ("val", "test")
    }
    balanced_counts = {
        split: dict(Counter(row["label_name"] for row in rows))
        for split, rows in balanced_rows.items()
    }

    texts: dict[str, str] = {}
    for split, rows in split_rows.items():
        texts[f"{split}.jsonl"] = jsonl_text(rows)
    for split, rows in balanced_rows.items():
        texts[f"{split}_balanced.jsonl"] = jsonl_text(rows)
    texts["classes.json"] = json_text(CLASSES)
    texts["label_mapping.json"] = json_text(
        {
            "schema": "cat-action-training-v1",
            "source": str(source),
            "source_sha256": sha256(source),
            "classes": CLASSES,
            "mapping": LABEL_MAPPING,
            "excluded_labels": sorted(EXCLUDED_LABELS),
            "abnormal_sources": sorted(
                label for label, target in LABEL_MAPPING.items()
                if target == "abnormal"
            ),
            "frame_numbering": FRAME_NUMBERING,
            "minimum_frames": MIN_FRAMES,
            "overlap_policy": "drop an interval if it overlaps any other interval in the same video",
        }
    )
    texts["split_manifest.json"] = json_text(
        {
            "schema": "cat-action-training-v1",
            "seed": split_seed,
            "split_days": {
                split: sorted(days) for split, days in split_groups.items()
            },
            "counts": split_counts,
            "balanced_counts": balanced_counts,
            "samples": {split: len(rows) for split, rows in split_rows.items()},
            "balanced_samples": {
                split: len(rows) for split, rows in balanced_rows.items()
            },
            "source_sha256": sha256(source),
            "frame_numbering": FRAME_NUMBERING,
            "minimum_frames": MIN_FRAMES,
            "classes": CLASSES,
        }
    )

    for name, text in texts.items():
        write_if_unchanged(out_dir / name, text, force)

    output_hashes = {
        name: sha256_text(text) for name, text in sorted(texts.items())
    }
    sha_lines = "".join(
        f"{output_hashes[name]}  {name}\n" for name in sorted(output_hashes)
    )
    write_if_unchanged(out_dir / "sha256sums.txt", sha_lines, force)

    source_hash_before = sha256(source)
    audit = {
        "schema": "cat-action-training-v1",
        "source": str(source),
        "source_sha256": source_hash_before,
        "source_rows": sum(1 for _ in read_source(source)),
        "frame_numbering": FRAME_NUMBERING,
        "minimum_frames": MIN_FRAMES,
        "overlap_policy": "drop an interval if it overlaps any other interval in the same video",
        "filter_counts": dict(filter_counts),
        "excluded_label_counts": dict(excluded_counts),
        "class_candidate_counts": class_counts,
        "candidate_total": len(candidates),
        "split_seed": split_seed,
        "split_days": {
            split: sorted(days) for split, days in split_groups.items()
        },
        "split_counts": split_counts,
        "split_samples": {split: len(rows) for split, rows in split_rows.items()},
        "balanced_counts": balanced_counts,
        "balanced_samples": {
            split: len(rows) for split, rows in balanced_rows.items()
        },
        "outputs": {
            "dir": str(out_dir),
            "files": sorted(list(texts) + ["sha256sums.txt"]),
            "sha256": output_hashes,
        },
        "video_check": video_check,
        "source_sha256_after": sha256(source),
    }
    if audit["source_sha256_after"] != source_hash_before:
        raise RuntimeError("Source annotation changed during index generation")
    write_if_unchanged(audit_path, json_text(audit), force)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-video-check", action="store_true",
                        help="Do not open videos to check frame ranges (tests only)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing derived outputs after backup")
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / "datasets/cat_raw/annotations/intervals.csv"
    videos_root = root / "datasets/cat_raw"
    if not source.is_file():
        raise FileNotFoundError(source)

    rows = read_source(source)
    candidates, filter_counts, excluded_counts, class_counts = build_candidates(rows)
    video_check = {"enabled": False}
    if not args.skip_video_check:
        candidates, video_check = verify_videos(candidates, videos_root)
        class_counts = dict(Counter(row["label_name"] for row in candidates))
    split_groups, split_seed = find_split(candidates)
    audit = write_outputs(
        root=root,
        source=source,
        candidates=candidates,
        split_groups=split_groups,
        split_seed=split_seed,
        filter_counts=filter_counts,
        excluded_counts=excluded_counts,
        class_counts=class_counts,
        video_check=video_check,
        force=args.force,
    )
    print(json.dumps({
        "candidate_total": audit["candidate_total"],
        "class_candidate_counts": audit["class_candidate_counts"],
        "split_seed": audit["split_seed"],
        "split_samples": audit["split_samples"],
        "split_counts": audit["split_counts"],
        "balanced_samples": audit["balanced_samples"],
        "source_sha256": audit["source_sha256"],
        "audit": str(root / "results/training/cat_action_v1/data_audit.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
