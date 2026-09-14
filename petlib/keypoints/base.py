"""关键点提取接口：动物关键点模型的统一抽象。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from petlib.schemas import KeypointSequence


class KeypointExtractor(ABC):
    """关键点提取器抽象：跟随视角视频/crop 序列 → 关键点序列（NPZ schema）。

    实现要求：
    - 重依赖（deeplabcut/mmpose）在 __init__ 内懒加载，缺失时抛出带指引的 ImportError
    - 输出 KeypointSequence（npz_dict 可直接 np.savez）
    """

    name: str = "base"
    num_keypoints: int = 0

    @abstractmethod
    def extract(self, video_path: str, boxes: list[tuple] | None = None) -> KeypointSequence:
        """对视频（可选：给定逐帧框先验）提取关键点序列。"""
