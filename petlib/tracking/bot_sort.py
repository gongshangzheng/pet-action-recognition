"""BoT-SORT 适配实现（简化）：ByteTrack 基础 + 相机运动补偿占位 + Re-ID 钩子占位。"""
from __future__ import annotations

from petlib.schemas import Detection, Track
from petlib.tracking.byte_track import ByteTrackTracker


class BoTSortTracker(ByteTrackTracker):
    """BoT-SORT 思路简化版：
    - 相机运动补偿（CMC）：占位——固定机位场景 CMC≈恒等，返回原框
    - Re-ID 外观特征：钩子保留（appearance_fn 可注入），默认禁用
    """

    name = "bot_sort"

    def __init__(self, appearance_fn=None, **kwargs):
        super().__init__(**kwargs)
        self.appearance_fn = appearance_fn  # Callable(img, box) -> np.ndarray | None

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        # CMC 占位：固定机位场景视为恒等变换；云台/运动机位需在此估计全局仿射
        return super().update(detections, frame_idx)
