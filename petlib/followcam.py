"""Shared camera smoothing for follow-camera video rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np


DEFAULT_MOVING_AVERAGE_WINDOW = 5
# Legacy channel names retained for compatibility. The first pair damps x1/y1
# coordinate deltas; the second pair damps x2/y2 coordinate deltas.
DEFAULT_OFFSET_ALPHA = 0.6
DEFAULT_OFFSET_MAX_VELOCITY = 0.05
DEFAULT_OFFSET_ALPHA_SIZE = 0.15
DEFAULT_OFFSET_MAX_VELOCITY_SIZE = 0.02


def centered_moving_average(
    values: Iterable[Iterable[float]] | Iterable[float],
    window_size: int = DEFAULT_MOVING_AVERAGE_WINDOW,
) -> np.ndarray:
    """Average along axis zero with edge padding at both sequence ends."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim not in (1, 2):
        raise ValueError("values must be a one- or two-dimensional sequence")
    if window_size < 1 or window_size % 2 != 1:
        raise ValueError("window_size must be a positive odd integer")
    if array.shape[0] == 0:
        return array.copy()

    radius = window_size // 2
    if array.ndim == 1:
        padded = np.pad(array, (radius, radius), mode="edge")
        kernel = np.ones(window_size, dtype=np.float64) / window_size
        return np.convolve(padded, kernel, mode="valid")

    padded = np.pad(array, ((radius, radius), (0, 0)), mode="edge")
    result = np.empty_like(array, dtype=np.float64)
    for column in range(array.shape[1]):
        result[:, column] = np.convolve(
            padded[:, column],
            np.ones(window_size, dtype=np.float64) / window_size,
            mode="valid",
        )
    return result


def cosine_anchor_weight(
    frame_index: int,
    previous_anchor: int | None,
    next_anchor: int | None,
    half_window: float,
) -> float:
    """Return a 0-at-anchor, 1-at-window-center cosine gating weight."""
    if half_window <= 0:
        raise ValueError("half_window must be positive")
    distances: list[int] = []
    if previous_anchor is not None:
        distances.append(frame_index - previous_anchor)
    if next_anchor is not None:
        distances.append(next_anchor - frame_index)
    if not distances:
        return 0.0
    if min(distances) < 0:
        raise ValueError("frame_index must lie between its anchor bounds")
    distance = min(distances)
    if distance == 0:
        return 0.0
    ratio = min(1.0, distance / half_window)
    return 0.5 * (1.0 - float(np.cos(np.pi * ratio)))


@dataclass
class MotionOffsetSmoother:
    """Smooth legacy xyxy coordinate channels with bounded state.

    The old baseline does not decompose an ``xyxy`` offset into center
    translation and width-height scale. Despite the retained parameter names,
    ``x1`` and ``y1`` form one coordinate pair and ``x2`` and ``y2`` another.
    """

    frame_width: float
    sample_stride: int
    translation_alpha: float = DEFAULT_OFFSET_ALPHA
    translation_max_velocity: float = DEFAULT_OFFSET_MAX_VELOCITY
    scale_alpha: float = DEFAULT_OFFSET_ALPHA_SIZE
    scale_max_velocity: float = DEFAULT_OFFSET_MAX_VELOCITY_SIZE
    offset: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )

    def __post_init__(self) -> None:
        if self.frame_width <= 0:
            raise ValueError("frame_width must be positive")
        if self.sample_stride < 1:
            raise ValueError("sample_stride must be positive")
        for name in (
            "translation_alpha",
            "translation_max_velocity",
            "scale_alpha",
            "scale_max_velocity",
        ):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        self.offset = np.asarray(self.offset, dtype=np.float64)
        if self.offset.shape != (4,):
            raise ValueError("offset must contain four box coordinates")

    def reset(self) -> None:
        self.offset.fill(0.0)

    def update(
        self,
        frame_index: int,
        base_box: Iterable[float],
        assisted_box: Iterable[float],
        previous_anchor: int | None,
        next_anchor: int | None,
    ) -> tuple[list[float], tuple[float, ...]]:
        """Advance one frame and return the smoothed assisted camera box."""
        base = np.asarray(base_box, dtype=np.float64)
        assisted = np.asarray(assisted_box, dtype=np.float64)
        if base.shape != (4,) or assisted.shape != (4,):
            raise ValueError("base_box and assisted_box must have four coordinates")

        if frame_index in (previous_anchor, next_anchor):
            self.reset()
            return base.tolist(), tuple(float(value) for value in self.offset)

        half_window = self.sample_stride / 2
        weight = cosine_anchor_weight(
            frame_index,
            previous_anchor,
            next_anchor,
            half_window,
        )
        target = (assisted - base) * weight
        velocity = np.asarray(
            [
                self.translation_max_velocity * self.frame_width,
                self.translation_max_velocity * self.frame_width,
                self.scale_max_velocity * self.frame_width,
                self.scale_max_velocity * self.frame_width,
            ],
            dtype=np.float64,
        )
        step = np.clip(target - self.offset, -velocity, velocity)
        self.offset[[0, 1]] += self.translation_alpha * step[[0, 1]]
        self.offset[[2, 3]] += self.scale_alpha * step[[2, 3]]
        return (
            (base + self.offset).tolist(),
            tuple(float(value) for value in self.offset),
        )
