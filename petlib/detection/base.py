"""检测接口：开放词汇/闭集检测器的统一抽象。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from petlib.schemas import Detection


class Detector(ABC):
    """检测器抽象：单帧 RGB(BGR ndarray) → 检测列表。

    实现要求：
    - 重依赖（transformers/ultralytics 等）必须在 __init__ 内懒加载
    - 输出 conf 须降序排列（方便下游取 argmax/top-k）
    """

    name: str = "base"

    @abstractmethod
    def detect(self, img_bgr: "np.ndarray", classes: tuple[str, ...] = ("cat",)) -> list[Detection]:
        """对单帧 BGR 图像检测指定类别（开放词汇实现将 classes 拼进 prompt）。"""

    def warmup(self, img_bgr: "np.ndarray | None" = None) -> None:
        """可选：预加载/预编译（默认无操作）。"""
