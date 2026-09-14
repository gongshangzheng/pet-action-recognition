"""跟踪接口：tracking-by-detection 跟踪器的统一抽象。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from petlib.schemas import Detection, Track


class Tracker(ABC):
    """跟踪器抽象：逐帧喂检测，内部维护轨迹状态。

    实现要求：
    - update() 逐帧调用（frame_idx 单调递增）
    - 返回当前活跃轨迹（每条含全部历史 TrackPoint，frame 单调递增）
    - finalize() 在视频结束时调用，返回全部轨迹（含已结束的）
    - 重依赖在 __init__ 内懒加载
    """

    name: str = "base"

    @abstractmethod
    def update(self, detections: list[Detection], frame_idx: int,
               frame: "np.ndarray | None" = None) -> list[Track]:
        """frame：当前帧图像（Re-ID/CMC 类跟踪器需要；纯运动跟踪器可忽略）。"""

    @abstractmethod
    def finalize(self) -> list[Track]: ...
