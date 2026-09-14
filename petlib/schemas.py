"""统一数据结构 + 序列化 schema 常量。零重依赖（仅标准库 + numpy）。

NPZ 关键点 schema（跨环境交接合同，见 design.md 约定）：
    keypoints (T,V,3) float16   # 逐帧 V 个关键点，第三通道 = 置信度
    frame_inds list[int]        # 帧索引（与 T 对齐）
    total_frames int
    source str
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

NPZ_KEYPOINTS_SCHEMA = "keypoints (T,V,3) float16, score in channel 2"
TRACK_JSON_SCHEMA = "{track_id, boxes:[{frame,x1,y1,x2,y2,conf,interpolated}]}"


@dataclass
class Detection:
    """单帧单目标检测。"""

    frame: int
    box: tuple[float, float, float, float]  # x1, y1, x2, y2（像素坐标）
    conf: float = 0.0
    cls: str = "cat"

    @property
    def width(self) -> float:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    def as_xywh(self) -> np.ndarray:
        return np.array([self.box[0], self.box[1], self.width, self.height], dtype=np.float64)


@dataclass
class TrackPoint:
    """轨迹上的单帧记录。"""

    frame: int
    box: tuple[float, float, float, float]
    conf: float = 0.0
    interpolated: bool = False


@dataclass
class Track:
    """一条目标轨迹（同一身份的逐帧框序列）。"""

    track_id: int
    boxes: list[TrackPoint] = field(default_factory=list)

    def last_frame(self) -> int:
        return self.boxes[-1].frame if self.boxes else -1

    def last_box(self) -> tuple | None:
        return self.boxes[-1].box if self.boxes else None

    def is_valid(self) -> bool:
        """schema 校验：frame 单调递增、box 四元组、conf 有限。"""
        if not self.boxes:
            return False
        frames = [p.frame for p in self.boxes]
        if any(b <= a for a, b in zip(frames, frames[1:])):
            return False
        for p in self.boxes:
            if len(p.box) != 4 or not all(np.isfinite(p.box)):
                return False
        return True


@dataclass
class KeypointSequence:
    """一段视频的关键点序列（NPZ schema 的内存形态）。"""

    kp: np.ndarray  # (T, V, 3) float16/32，第三通道 = 置信度
    frame_inds: list[int]
    total_frames: int
    source: str = ""

    def validate(self) -> bool:
        if self.kp.ndim != 3 or self.kp.shape[1] != len(self.frame_inds) and self.kp.shape[0] != len(self.frame_inds):
            return False
        return bool(np.all(np.isfinite(self.kp) | (self.kp == 0)))

    def to_npz_dict(self) -> dict:
        return {
            "keypoints": self.kp.astype(np.float16),
            "frame_inds": np.asarray(self.frame_inds, dtype=np.int64),
            "total_frames": int(self.total_frames),
            "source": np.asarray(self.source),
        }
