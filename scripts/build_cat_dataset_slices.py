#!/usr/bin/env python3
"""Build the cat/dog behaviour clip dataset from annotated intervals.

Pipeline (order matters, each interval leaves with exactly one reason):

1. drop labels outside the closed set (multi_cat_chase, multi_cat_roughplay)
2. drop intervals shorter than 1 second (annotation points, not ranges)
3. classify by pet count on detection anchors: multi-pet / no-detection / single
4. assign a split by event day, using the frozen day map when the interval is new
5. arbitrate overlaps: specific behaviour > activity > prolonged_stationary
6. extend short intervals to one clip length using real neighbouring frames
7. slice into clips with stratified random starts, at most four per interval
8. cap the activity class at three times the second-largest class

No video is re-encoded; the output is a clip manifest plus a summary of losses.
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
from typing import Any

LABEL_MAP = {
    "common/activity": "activity",
    "common/eating": "eating",
    "common/drinking": "drinking",
    "common/prolonged_stationary": "prolonged_stationary",
    "common/grooming": "grooming",
    "common/toileting": "toileting",
    "abnormal/scratching": "scratching",
    "abnormal/gnawing": "gnawing",
    "abnormal/fall": "fall",
    "abnormal/seizure": "seizure",
}
DROPPED_LABELS = {"common/multi_cat_chase", "common/multi_cat_roughplay"}
LOW_PRIORITY = {"activity": 1, "prolonged_stationary": 0}
DEFAULT_PRIORITY = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--detection-dir", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--clip-frames", type=int, default=60)
    parser.add_argument("--max-clips", type=int, default=4)
    parser.add_argument("--min-frames", type=int, default=15)
    parser.add_argument("--pet-coverage", type=float, default=0.5)
    parser.add_argument("--pet-run", type=int, default=3)
    parser.add_argument("--activity-cap-ratio", type=float, default=3.0)
    parser.add_argument("--fps", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0, help="process only the first N intervals")
    return parser.parse_args()


def event_day(video: str) -> str | None:
    match = re.search(r"event_(\d{8})_", video)
    return match.group(1) if match else None


def load_day_splits(path: Path) -> dict[str, str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for split, days in manifest["split_days"].items():
        for day in days:
            mapping[str(day)] = split
    return mapping


def load_detections(detection_dir: Path) -> dict[str, dict[str, Any]]:
    """Load detection caches: per-video anchors, stride and frame count."""
    caches = {}
    for path in detection_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "complete":
            continue
        caches[payload["video"].split("/")[-1]] = payload
    return caches


def anchors_in(cache: dict[str, Any], start: int, end: int) -> list[dict[str, Any]]:
    anchors = cache["anchors"]
    return [anchors[key] for key in anchors if start <= int(key) <= end]


def pet_flags(states: list[dict[str, Any]]) -> list[bool]:
    return [((s.get("cat_count") or 0) + (s.get("dog_count") or 0)) >= 2 for s in states]


def species_of(states: list[dict[str, Any]]) -> str:
    cats = sum(1 for s in states if (s.get("cat_count") or 0) > 0)
    dogs = sum(1 for s in states if (s.get("dog_count") or 0) > 0)
    return "dog" if dogs > cats else "cat"


def longest_run(flags: list[bool]) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def clip_starts(length: int, clip: int, max_clips: int, rng: random.Random) -> list[int]:
    capacity = max(1, length // clip) if length >= clip else 1
    count = min(max_clips, capacity)
    if length <= clip:
        return [0]
    starts = []
    span = length - clip
    for index in range(count):
        if count == 1:
            starts.append(rng.randint(0, span))
        else:
            low = round(span * index / count)
            high = round(span * (index + 1) / count)
            starts.append(rng.randint(low, max(low, high)))
    return sorted(set(starts))


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    day_splits = load_day_splits(args.split_manifest)
    caches = load_detections(args.detection_dir)
    rows = list(csv.DictReader(args.intervals.open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]

    losses: Counter = Counter()
    by_class_loss: dict[str, Counter] = defaultdict(Counter)
    survivors: list[dict[str, Any]] = []

    for row in rows:
        label = row["label"]
        if label in DROPPED_LABELS:
            losses["unmapped_label"] += 1
            continue
        mapped = LABEL_MAP[label]
        start, end = int(row["start_frame"]), int(row["end_frame"])
        length = end - start + 1
        if length < args.min_frames:
            losses["too_short"] += 1
            by_class_loss[mapped]["too_short"] += 1
            continue
        stem = row["video"].split("/")[-1]
        cache = caches.get(stem)
        if cache is None:
            losses["no_detection"] += 1
            by_class_loss[mapped]["no_detection"] += 1
            continue
        states = anchors_in(cache, start, end)
        flags = pet_flags(states)
        if not flags:
            losses["no_detection"] += 1
            by_class_loss[mapped]["no_detection"] += 1
            continue
        coverage = sum(flags) / len(flags)
        if coverage >= args.pet_coverage and longest_run(flags) >= args.pet_run:
            losses["multi_pet"] += 1
            by_class_loss[mapped]["multi_pet"] += 1
            continue
        species = species_of(states)
        day = event_day(stem)
        split = day_splits.get(day, "unassigned") if day else "unassigned"
        if split == "unassigned":
            losses["unassigned_split"] += 1
            by_class_loss[mapped]["unassigned_split"] += 1
            continue
        survivors.append(
            {
                "sample_id": row.get("annotation_id") or f"{stem}:{start}-{end}",
                "video": row["video"],
                "label": mapped,
                "species": species,
                "split": split,
                "start": start,
                "end": end,
                "aligned": True,
                "suppressed_by": None,
            }
        )

    # overlap arbitration within each video
    by_video: dict[str, list[dict]] = defaultdict(list)
    for item in survivors:
        by_video[item["video"]].append(item)
    arbitrated: list[dict] = []
    for video, items in by_video.items():
        items.sort(key=lambda r: (r["start"], -r["end"]))
        kept: list[dict] = []
        for item in items:
            winner = None
            for other in kept:
                if item["start"] <= other["end"] and other["start"] <= item["end"]:
                    pi = LOW_PRIORITY.get(item["label"], DEFAULT_PRIORITY)
                    po = LOW_PRIORITY.get(other["label"], DEFAULT_PRIORITY)
                    if po > pi or (po == pi and other["end"] - other["start"] >= item["end"] - item["start"]):
                        winner = other
                        break
            if winner is not None:
                losses["overlap_suppressed"] += 1
                by_class_loss[item["label"]]["overlap_suppressed"] += 1
                winner["suppressed_by"] = winner["suppressed_by"] or []
                winner["suppressed_by"].append(item["sample_id"])
            else:
                kept.append(item)
        arbitrated.extend(kept)

    total_frames = {
        stem: int(cache.get("decoded_frames") or 0) for stem, cache in caches.items()
    }

    # neighbour boundaries: extension must not swallow another interval
    neighbours: dict[str, tuple[int, int]] = {}
    per_video: dict[str, list[dict]] = defaultdict(list)
    for item in arbitrated:
        per_video[item["video"]].append(item)
    for video, items in per_video.items():
        items.sort(key=lambda r: r["start"])
        limit = total_frames.get(video.split("/")[-1], 0)
        for index, item in enumerate(items):
            lower = items[index - 1]["end"] + 1 if index else 1
            upper = items[index + 1]["start"] - 1 if index + 1 < len(items) else limit
            neighbours[item["sample_id"]] = (lower, upper)

    # extension and slicing
    clips: list[dict[str, Any]] = []
    for item in arbitrated:
        length = item["end"] - item["start"] + 1
        start, end = item["start"], item["end"]
        extended = False
        if length < args.clip_frames:
            stem = item["video"].split("/")[-1]
            limit = total_frames.get(stem, 0)
            lower, upper = neighbours.get(item["sample_id"], (1, limit))
            need = args.clip_frames - length
            left_room = start - lower
            right_room = upper - end
            take_left = min(max(0, left_room), need // 2)
            take_right = min(max(0, right_room), need - take_left)
            short = need - take_left - take_right
            if short > 0:
                extra_left = min(max(0, left_room - take_left), short)
                take_left += extra_left
                short -= extra_left
            if short > 0:
                take_right += min(max(0, right_room - take_right), short)
            new_start = start - take_left
            new_end = end + take_right
            if new_end - new_start + 1 < args.clip_frames:
                losses["extension_failed"] += 1
                by_class_loss[item["label"]]["extension_failed"] += 1
                continue
            start, end = new_start, new_end
            extended = True
        length = end - start + 1
        for offset in clip_starts(length, args.clip_frames, args.max_clips, rng):
            clip_start = start + offset
            clip_end = min(clip_start + args.clip_frames - 1, end)
            clips.append(
                {
                    "sample_id": item["sample_id"],
                    "video": item["video"],
                    "label": item["label"],
                    "species": item["species"],
                    "split": item["split"],
                    "start": clip_start,
                    "end": clip_end,
                    "extended": extended,
                    "shorter_than_clip": (clip_end - clip_start + 1) < args.clip_frames,
                    "suppressed_by": item.get("suppressed_by"),
                }
            )

    # activity cap
    counts = Counter(clip["label"] for clip in clips)
    others = sorted(
        (value for label, value in counts.items() if label != "activity"), reverse=True
    )
    cap = int(others[0] * args.activity_cap_ratio) if others else 0
    if counts.get("activity", 0) > cap:
        victims = [c for c in clips if c["label"] == "activity"]
        rng.shuffle(victims)
        drop_ids = {id(c) for c in victims[: counts["activity"] - cap]}
        clips = [c for c in clips if id(c) not in drop_ids]
        losses["activity_capped"] += len(drop_ids)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "clips.jsonl").open("w", encoding="utf-8") as stream:
        for clip in clips:
            stream.write(json.dumps(clip, ensure_ascii=False) + "\n")
    summary = {
        "schema": "cat-dataset-slices-v1",
        "seed": args.seed,
        "params": {
            "clip_frames": args.clip_frames,
            "max_clips": args.max_clips,
            "min_frames": args.min_frames,
            "pet_coverage": args.pet_coverage,
            "pet_run": args.pet_run,
            "activity_cap_ratio": args.activity_cap_ratio,
            "fps": args.fps,
        },
        "intervals_in": len(rows),
        "intervals_used": len(arbitrated),
        "clips": len(clips),
        "losses": dict(losses),
        "losses_by_class": {k: dict(v) for k, v in by_class_loss.items()},
        "clips_by_label": dict(Counter(c["label"] for c in clips)),
        "clips_by_species": dict(Counter(c["species"] for c in clips)),
        "clips_by_split": dict(Counter(c["split"] for c in clips)),
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in ("intervals_in", "intervals_used", "clips", "losses", "clips_by_label")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
