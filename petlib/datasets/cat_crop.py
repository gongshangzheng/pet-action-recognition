"""Geometry and eligibility rules for the cat crop experiment."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import cv2
import numpy as np


def box_iou(left: Iterable[float], right: Iterable[float]) -> float:
    """Return intersection over union for two ``x1, y1, x2, y2`` boxes."""
    ax1, ay1, ax2, ay2 = map(float, left)
    bx1, by1, bx2, by2 = map(float, right)
    inter_width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = inter_width * inter_height
    union = (
        max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        + max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        - intersection
    )
    return intersection / max(1e-6, union)


def clip_box(
    box: Iterable[float], width: int, height: int
) -> tuple[float, float, float, float]:
    """Clamp a box to the image while preserving a non-empty interior."""
    x1, y1, x2, y2 = map(float, box)
    x1 = min(max(0.0, x1), max(0.0, width - 1.0))
    y1 = min(max(0.0, y1), max(0.0, height - 1.0))
    x2 = min(max(x1 + 1.0, x2), float(width))
    y2 = min(max(y1 + 1.0, y2), float(height))
    return x1, y1, x2, y2


def deduplicate_detections(
    detections: Iterable[dict[str, Any]], iou_threshold: float = 0.55
) -> list[dict[str, Any]]:
    """Deduplicate detections independently per class, keeping highest scores."""
    kept: list[dict[str, Any]] = []
    ordered = sorted(detections, key=lambda row: float(row["confidence"]), reverse=True)
    for detection in ordered:
        same_class = [
            row
            for row in kept
            if row["class"] == detection["class"]
            and box_iou(row["box"], detection["box"]) >= iou_threshold
        ]
        if not same_class:
            kept.append(dict(detection))
    return kept


def classify_frame(
    detections: Iterable[dict[str, Any]],
    width: int,
    height: int,
    iou_threshold: float = 0.55,
) -> dict[str, Any]:
    """Describe pet count, species and target ambiguity for one frame."""
    kept = deduplicate_detections(detections, iou_threshold)
    cats = sorted(
        (row for row in kept if row["class"] == "cat"),
        key=lambda row: float(row["confidence"]),
        reverse=True,
    )
    dogs = sorted(
        (row for row in kept if row["class"] == "dog"),
        key=lambda row: float(row["confidence"]),
        reverse=True,
    )
    for row in (*cats, *dogs):
        row["box"] = list(clip_box(row["box"], width, height))

    pets = sorted((*cats, *dogs), key=lambda row: float(row["confidence"]), reverse=True)
    reasons: list[str] = []
    if not pets:
        reasons.append("no_reliable_pet_detection")
    elif len(pets) > 1:
        reasons.append("multi_pet_unsupported")
    return {
        "cat_count": len(cats),
        "dog_count": len(dogs),
        "pet_count": len(pets),
        "target_class": pets[0]["class"] if pets else None,
        "target_box": pets[0]["box"] if pets else None,
        "target_confidence": float(pets[0]["confidence"]) if pets else None,
        "cat_candidates": cats,
        "dog_candidates": dogs,
        "reasons": reasons,
        "target_valid": not reasons,
    }


def target_box(state: dict[str, Any]) -> list[float] | None:
    """Return the target box and accept legacy cat-only caches."""
    return state.get("target_box") or state.get("cat_box")


def target_class(state: dict[str, Any]) -> str | None:
    """Return the target species and accept legacy cat-only caches."""
    return state.get("target_class") or ("cat" if state.get("cat_box") else None)


def missing_pet_reasons(state: dict[str, Any]) -> bool:
    reasons = set(state.get("reasons") or [])
    return bool(
        reasons
        & {"no_reliable_pet_detection", "no_reliable_cat_detection"}
    )


def multi_pet_reasons(state: dict[str, Any]) -> bool:
    reasons = set(state.get("reasons") or [])
    return bool(
        reasons
        & {
            "multi_pet_unsupported",
            "multi_cat_target_ambiguous",
            "dog_present_target_ambiguous",
        }
    )


def build_frame_track(
    anchors: dict[int, dict[str, Any]],
    total_frames: int,
    sample_stride: int,
    max_gap: int | None = None,
) -> list[dict[str, Any]]:
    """Build the strict crop track and a separate best-cat display track.

    ``camera_box`` follows the training eligibility rules. ``display_box`` keeps
    the highest-confidence pet box for review rendering even when an unsupported
    multi-pet frame is excluded from training.
    """
    if sample_stride < 1:
        raise ValueError("sample_stride must be positive")
    if total_frames < 1:
        raise ValueError("total_frames must be positive")
    max_gap = max_gap or sample_stride * 2
    clean = {
        int(frame): target_box(state)
        for frame, state in anchors.items()
        if state.get("target_valid") and target_box(state) is not None
    }
    clean_frames = sorted(frame for frame in clean if 0 <= frame < total_frames)
    track: list[dict[str, Any]] = [
        {
            "frame": frame,
            "frame_index_base": 0,
            "camera_box": None,
            "display_box": None,
            "source": "invalid",
            "valid": False,
            "reason": "no_reliable_pet_detection",
        }
        for frame in range(total_frames)
    ]

    for anchor_index, frame in enumerate(clean_frames):
        state = anchors[frame]
        track[frame] = {
            "frame": frame,
            "frame_index_base": 0,
            "camera_box": [round(float(value), 3) for value in clean[frame]],
            "display_box": [round(float(value), 3) for value in clean[frame]],
            "source": "detected",
            "valid": True,
            "reason": None,
            "cat_count": state.get("cat_count"),
            "dog_count": state.get("dog_count"),
            "pet_count": state.get("pet_count"),
            "target_class": target_class(state),
        }
        if anchor_index + 1 >= len(clean_frames):
            continue
        next_frame = clean_frames[anchor_index + 1]
        next_state = anchors[next_frame]
        if target_class(state) != target_class(next_state):
            continue
        gap = next_frame - frame
        if any(
            frame < invalid_frame < next_frame
            and multi_pet_reasons(anchors[invalid_frame])
            for invalid_frame in anchors
        ):
            continue
        if gap <= 1 or gap > max_gap:
            continue
        left = np.asarray(clean[frame], dtype=np.float64)
        right = np.asarray(clean[next_frame], dtype=np.float64)
        for intermediate in range(frame + 1, next_frame):
            weight = (intermediate - frame) / gap
            box = left + weight * (right - left)
            track[intermediate] = {
                "frame": intermediate,
                "frame_index_base": 0,
                "camera_box": [round(float(value), 3) for value in box],
                "source": "interpolated",
                "valid": True,
                "reason": None,
            }

    for frame, state in anchors.items():
        if not (0 <= frame < total_frames) or state.get("target_valid"):
            continue
        reasons = state.get("reasons") or ["no_reliable_pet_detection"]
        if (
            missing_pet_reasons(state)
            and track[frame].get("valid")
            and track[frame].get("source") == "interpolated"
        ):
            track[frame]["missing_detection_bridged"] = True
            continue
        track[frame] = {
            "frame": frame,
            "frame_index_base": 0,
            "camera_box": None,
            "display_box": (
                [round(float(value), 3) for value in target_box(state)]
                if target_box(state) is not None
                else None
            ),
            "source": "invalid",
            "valid": False,
            "reason": reasons[0],
            "reasons": reasons,
            "cat_count": state.get("cat_count"),
            "dog_count": state.get("dog_count"),
            "pet_count": state.get("pet_count"),
            "target_class": target_class(state),
        }

    display_frames = sorted(
        frame
        for frame, state in anchors.items()
        if target_box(state) is not None and 0 <= frame < total_frames
    )
    for current, following in zip(display_frames, display_frames[1:]):
        gap = following - current
        if gap <= 1 or gap > max_gap:
            continue
        left = np.asarray(target_box(anchors[current]), dtype=np.float64)
        right = np.asarray(target_box(anchors[following]), dtype=np.float64)
        for intermediate in range(current + 1, following):
            if track[intermediate].get("display_box") is not None:
                continue
            weight = (intermediate - current) / gap
            box = left + weight * (right - left)
            track[intermediate]["display_box"] = [
                round(float(value), 3) for value in box
            ]
    return track


def interval_status(
    start_frame: int, end_frame: int, track: list[dict[str, Any]]
) -> dict[str, Any]:
    """Check every frame in a 1-based inclusive interval against the track."""
    if start_frame < 1 or end_frame < start_frame or end_frame > len(track):
        return {
            "eligible": False,
            "reason": "invalid_frame_range",
            "invalid_frames": 0,
        }
    invalid = [
        row for row in track[start_frame - 1 : end_frame] if not row.get("valid")
    ]
    target_classes = {
        row.get("target_class")
        for row in track[start_frame - 1 : end_frame]
        if row.get("valid") and row.get("target_class") is not None
    }
    if not invalid and len(target_classes) > 1:
        return {
            "eligible": False,
            "reason": "target_species_changed",
            "invalid_frames": 0,
            "valid_frames": end_frame - start_frame + 1,
        }
    if not invalid:
        return {
            "eligible": True,
            "reason": None,
            "invalid_frames": 0,
            "valid_frames": end_frame - start_frame + 1,
        }
    reasons = Counter(row.get("reason") or "track_invalid" for row in invalid)
    priority = (
        "multi_pet_unsupported",
        "multi_cat_target_ambiguous",
        "dog_present_target_ambiguous",
        "no_reliable_pet_detection",
        "no_reliable_cat_detection",
    )
    reason = next(
        (name for name in priority if reasons[name]), reasons.most_common(1)[0][0]
    )
    return {
        "eligible": False,
        "reason": reason,
        "invalid_frames": len(invalid),
        "valid_frames": end_frame - start_frame + 1 - len(invalid),
        "reason_counts": dict(reasons),
    }


def crop_bounds(
    box: Iterable[float],
    frame_width: int,
    frame_height: int,
    pad: float = 1.2,
) -> tuple[int, int, int, int]:
    """Return a clipped square around a box before resizing."""
    if pad < 1:
        raise ValueError("pad must be at least 1")
    x1, y1, x2, y2 = map(float, box)
    side = max(x2 - x1, y2 - y1) * pad
    if side <= 0:
        raise ValueError("box has no area")
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    left = int(max(0, center_x - side / 2))
    top = int(max(0, center_y - side / 2))
    right = int(min(frame_width, center_x + side / 2))
    bottom = int(min(frame_height, center_y + side / 2))
    if right <= left or bottom <= top:
        raise ValueError("box produces an empty crop")
    return left, top, right, bottom


def crop_square(
    frame: np.ndarray,
    box: Iterable[float],
    size: int,
    pad: float = 1.2,
) -> np.ndarray:
    """Crop around ``box`` and resize the resulting pixels to a square."""
    if frame.ndim != 3 or frame.shape[0] < 1 or frame.shape[1] < 1:
        raise ValueError("frame must be a non-empty HxWxC image")
    left, top, right, bottom = crop_bounds(box, frame.shape[1], frame.shape[0], pad)
    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        raise ValueError("empty crop")
    return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)


def letterbox_square(
    frame: np.ndarray,
    size: int,
    background: int = 32,
) -> np.ndarray:
    """Fit a complete frame into a square with neutral margins."""
    if frame.ndim != 3 or frame.shape[0] < 1 or frame.shape[1] < 1:
        raise ValueError("frame must be a non-empty HxWxC image")
    height, width = frame.shape[:2]
    scale = min(size / width, size / height)
    resized = cv2.resize(
        frame,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    vertical = size - resized.shape[0]
    horizontal = size - resized.shape[1]
    return cv2.copyMakeBorder(
        resized,
        vertical // 2,
        vertical - vertical // 2,
        horizontal // 2,
        horizontal - horizontal // 2,
        cv2.BORDER_CONSTANT,
        value=(background, background, background),
    )


def motion_correct_box(
    foreground: np.ndarray,
    box: Iterable[float],
    previous_hit: bool,
    min_coverage: float = 0.2,
    max_expansion_ratio: float = 0.25,
) -> tuple[list[float], bool, bool]:
    """Expand one interpolated box from a foreground component."""
    x1, y1, x2, y2 = map(float, box)
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        raise ValueError("box has no area")
    contours, _ = cv2.findContours(
        foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    best = None
    best_intersection = 0.0
    for contour in contours:
        bx, by, bw, bh = cv2.boundingRect(contour)
        intersect_width = max(0.0, min(x2, bx + bw) - max(x1, bx))
        intersect_height = max(0.0, min(y2, by + bh) - max(y1, by))
        intersection = intersect_width * intersect_height
        if intersection > best_intersection:
            best_intersection = intersection
            best = (bx, by, bw, bh)
    hit_now = bool(
        best is not None
        and best_intersection / max(1.0, width * height) >= min_coverage
    )
    if not (hit_now and previous_hit):
        return [x1, y1, x2, y2], False, hit_now

    bx, by, bw, bh = best
    expanded = [
        max(min(x1, bx), x1 - max_expansion_ratio * width),
        max(min(y1, by), y1 - max_expansion_ratio * height),
        min(max(x2, bx + bw), x2 + max_expansion_ratio * width),
        min(max(y2, by + bh), y2 + max_expansion_ratio * height),
    ]
    corrected = any(
        abs(new - old) > 0.5 for new, old in zip(expanded, (x1, y1, x2, y2))
    )
    return expanded, corrected, hit_now
