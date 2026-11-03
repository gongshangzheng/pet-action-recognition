#!/usr/bin/env python3
"""Select a deterministic, class-balanced sample for cat-crop inspection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

CLASSES = (
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
)
DEFAULT_TRAIN_INDEX = Path("/home/wyy/pet-final-v1/datasets/cat_action_v1/train.jsonl")
DEFAULT_OUT = Path(
    "/home/wyy/pet-action-recognition/results/cat_crop_classification/"
    "gdino-crop-20261103a/quality/sample20/selection.json"
)
DEFAULT_SALT = "gdino-crop-20261103a-quality-v1"
NIGHT_HOURS = frozenset((*range(0, 6), *range(20, 24)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_score(row: dict[str, Any], salt: str) -> str:
    value = f"{salt}:{row['sample_id']}"
    return hashlib.sha256(value.encode()).hexdigest()


def event_hour(video: str) -> int | None:
    match = re.search(r"event_\d{8}_(\d{2})\d{4}\.mp4$", Path(video).name)
    return int(match.group(1)) if match else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _validate_selection_inputs(
    rows: Iterable[dict[str, Any]],
    *,
    per_class: int,
    short_count: int,
    long_count: int,
    night_count: int,
    target_total: int,
) -> list[dict[str, Any]]:
    if per_class < 1:
        raise ValueError("per_class must be positive")
    if min(short_count, long_count, night_count) < 0:
        raise ValueError("supplemental quotas must be non-negative")
    required_total = len(CLASSES) * per_class + short_count + long_count + night_count
    if target_total != required_total:
        raise ValueError(
            f"target_total must equal class plus supplemental quotas ({required_total})"
        )

    validated: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    for position, original in enumerate(rows):
        row = dict(original)
        sample_id = row.get("sample_id")
        video = row.get("video")
        label = row.get("label")
        start_frame = row.get("start_frame")
        end_frame = row.get("end_frame")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"row {position} has an invalid sample_id")
        if sample_id in sample_ids:
            raise ValueError(f"duplicate sample_id {sample_id}")
        if not isinstance(video, str) or not video:
            raise ValueError(f"{sample_id} has an invalid video")
        if not isinstance(label, int) or isinstance(label, bool):
            raise ValueError(f"{sample_id} has a non-integer label")
        if label < 0 or label >= len(CLASSES):
            raise ValueError(f"{sample_id} has invalid class label {label}")
        for name, value in (
            ("start_frame", start_frame),
            ("end_frame", end_frame),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{sample_id} has a non-integer {name}")
        if start_frame < 1 or end_frame < start_frame:
            raise ValueError(f"{sample_id} has an invalid frame interval")
        row["video"] = str(PurePosixPath(video))
        validated.append(row)
        sample_ids.add(sample_id)
    return validated


def _remaining_rows(
    rows: Iterable[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row["sample_id"]) not in selected_ids
        and str(row["video"]) not in selected_videos
    ]


def _add_row(
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
    row: dict[str, Any],
    reason: str,
) -> bool:
    sample_id = str(row["sample_id"])
    video = str(row["video"])
    if sample_id in selected_ids or video in selected_videos:
        return False
    enriched = dict(row)
    enriched["class_name"] = CLASSES[int(row["label"])]
    enriched["frame_count"] = int(row["end_frame"]) - int(row["start_frame"]) + 1
    enriched["event_hour"] = event_hour(video)
    enriched["selection_reasons"] = [reason]
    selected.append(enriched)
    selected_ids.add(sample_id)
    selected_videos.add(video)
    return True


def _add_quota(
    candidates: Iterable[dict[str, Any]],
    quota: int,
    reason: str,
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
) -> int:
    added = 0
    for row in candidates:
        if added == quota:
            break
        added += int(
            _add_row(
                selected,
                selected_ids,
                selected_videos,
                row,
                reason,
            )
        )
    if added != quota:
        raise ValueError(
            f"insufficient unique candidates for {reason}: {added}/{quota}"
        )
    return added


def _select_night_strata(
    source_rows: list[dict[str, Any]],
    salt: str,
    night_count: int,
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
) -> None:
    candidates = sorted(
        (
            row
            for row in source_rows
            if event_hour(str(row["video"])) in NIGHT_HOURS
        ),
        key=lambda row: stable_score(row, salt),
    )
    _add_quota(
        candidates,
        night_count,
        "timestamp_night_candidate",
        selected,
        selected_ids,
        selected_videos,
    )


def _select_class_strata(
    source_rows: list[dict[str, Any]],
    salt: str,
    per_class: int,
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
) -> None:
    by_class: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        by_class[int(row["label"])].append(row)
    for label in range(len(CLASSES)):
        candidates = sorted(
            by_class[label], key=lambda row: stable_score(row, salt)
        )
        _add_quota(
            candidates,
            per_class,
            f"class_stratified:{CLASSES[label]}",
            selected,
            selected_ids,
            selected_videos,
        )


def _select_duration_strata(
    source_rows: list[dict[str, Any]],
    salt: str,
    short_count: int,
    long_count: int,
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    selected_videos: set[str],
) -> None:
    def duration_key(row: dict[str, Any]) -> tuple[int, str]:
        return (
            int(row["end_frame"]) - int(row["start_frame"]) + 1,
            stable_score(row, salt),
        )

    shortest = sorted(
        _remaining_rows(source_rows, selected_ids, selected_videos),
        key=duration_key,
    )
    _add_quota(
        shortest,
        short_count,
        "shortest_duration",
        selected,
        selected_ids,
        selected_videos,
    )
    longest = sorted(
        _remaining_rows(source_rows, selected_ids, selected_videos),
        key=duration_key,
        reverse=True,
    )
    _add_quota(
        longest,
        long_count,
        "longest_duration",
        selected,
        selected_ids,
        selected_videos,
    )


def select_quality_rows(
    rows: Iterable[dict[str, Any]],
    *,
    salt: str = DEFAULT_SALT,
    per_class: int = 2,
    short_count: int = 2,
    long_count: int = 2,
    night_count: int = 2,
    target_total: int = 20,
) -> list[dict[str, Any]]:
    """Select unique videos before inspecting detection or crop outcomes."""
    source_rows = _validate_selection_inputs(
        rows,
        per_class=per_class,
        short_count=short_count,
        long_count=long_count,
        night_count=night_count,
        target_total=target_total,
    )

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_videos: set[str] = set()

    _select_night_strata(
        source_rows,
        salt,
        night_count,
        selected,
        selected_ids,
        selected_videos,
    )
    _select_class_strata(
        source_rows,
        salt,
        per_class,
        selected,
        selected_ids,
        selected_videos,
    )
    _select_duration_strata(
        source_rows,
        salt,
        short_count,
        long_count,
        selected,
        selected_ids,
        selected_videos,
    )
    if len(selected) != target_total:
        raise AssertionError(f"selected {len(selected)} rows, expected {target_total}")
    return sorted(selected, key=lambda row: row["sample_id"])


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-index", type=Path, default=DEFAULT_TRAIN_INDEX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--salt", default=DEFAULT_SALT)
    args = parser.parse_args()

    rows = read_jsonl(args.train_index)
    selected = select_quality_rows(rows, salt=args.salt)
    payload = {
        "schema": "cat-crop-quality-selection-v1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "train_index": str(args.train_index),
        "train_index_sha256": sha256(args.train_index),
        "rule": {
            "salt": args.salt,
            "per_class": 2,
            "short_count": 2,
            "long_count": 2,
            "night_count": 2,
            "target_total": 20,
            "night_hours_filename_clock": sorted(NIGHT_HOURS),
            "unique_videos": True,
            "selected_before_detection": True,
        },
        "rows": selected,
        "videos": [row["video"] for row in selected],
        "class_counts": {
            class_name: sum(row["class_name"] == class_name for row in selected)
            for class_name in CLASSES
        },
    }
    atomic_json(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
