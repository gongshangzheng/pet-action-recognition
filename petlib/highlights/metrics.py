"""亮点抓取的逐帧指标：纯 numpy 实现，便于端侧移植。

坐标与掩码均在“分析分辨率”下；所有比例量与分辨率无关。
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

Box = Tuple[float, float, float, float]  # x1, y1, x2, y2（像素）；用 typing 以兼容端侧 Python 3.8


def luma(frame_bgr: np.ndarray) -> np.ndarray:
    """BT.601 亮度，float32，范围 0–255。接受 BGR 三通道或单通道。"""
    if frame_bgr.ndim == 2:
        return frame_bgr.astype(np.float32)
    f = frame_bgr.astype(np.float32)
    return 0.114 * f[..., 0] + 0.587 * f[..., 1] + 0.299 * f[..., 2]


def brightness(y: np.ndarray) -> float:
    """整帧平均亮度 / 255，范围 0–1。"""
    return float(y.mean() / 255.0)


def contrast_rms(y: np.ndarray) -> float:
    """RMS 对比度 = 亮度标准差 / 255，范围 0–0.5。"""
    return float(y.std() / 255.0)


def contrast_spread(y: np.ndarray, lo: float = 5.0, hi: float = 95.0) -> float:
    """亮度 p5–p95 跨度 / 255；对少量过曝/死黑像素不敏感。"""
    p_lo, p_hi = np.percentile(y, [lo, hi])
    return float((p_hi - p_lo) / 255.0)


def clip_box(box: Box, width: int, height: int) -> tuple[int, int, int, int]:
    """把浮点框裁到画面内并取整，返回 (x1, y1, x2, y2)，x2/y2 为开区间。"""
    x1, y1, x2, y2 = box
    xi1 = int(np.clip(np.floor(x1), 0, width))
    yi1 = int(np.clip(np.floor(y1), 0, height))
    xi2 = int(np.clip(np.ceil(x2), 0, width))
    yi2 = int(np.clip(np.ceil(y2), 0, height))
    return xi1, yi1, max(xi1, xi2), max(yi1, yi2)


def expand_box(box: Box, ratio: float) -> Box:
    """以框中心为基准，宽高各外扩 ratio（0.1 = 每边各 5%，总计 10%）。"""
    x1, y1, x2, y2 = box
    dw = (x2 - x1) * ratio / 2.0
    dh = (y2 - y1) * ratio / 2.0
    return x1 - dw, y1 - dh, x2 + dw, y2 + dh


def boxes_mask(boxes: list[Box], shape: tuple[int, int]) -> np.ndarray:
    """多个框的并集布尔掩码，shape = (H, W)。"""
    h, w = shape
    m = np.zeros((h, w), dtype=bool)
    for b in boxes:
        x1, y1, x2, y2 = clip_box(b, w, h)
        m[y1:y2, x1:x2] = True
    return m


def area_ratio(mask: np.ndarray) -> float:
    """掩码像素占整帧比例。"""
    return float(mask.mean()) if mask.size else 0.0


def centroid(mask: np.ndarray) -> tuple[float, float] | None:
    """掩码质心 (x, y)；空掩码返回 None。"""
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return float(xs.mean()), float(ys.mean())


def motion_energy(prev_y: np.ndarray, y: np.ndarray, region: np.ndarray) -> dict:
    """宠物区域运动能量（含全局变化补偿）。

    返回 inside / outside / activity：
    - inside：区域内 |ΔY|/255 均值
    - outside：区域外 |ΔY|/255 均值（光照变化、云台转动等全局变化）
    - activity：max(0, inside - outside)；区域为空时为 0
    """
    diff = np.abs(y - prev_y) / 255.0
    n_in = int(region.sum())
    n_out = region.size - n_in
    inside = float(diff[region].mean()) if n_in else 0.0
    outside = float(diff[~region].mean()) if n_out else 0.0
    activity = max(0.0, inside - outside) if n_in else 0.0
    return {"inside": inside, "outside": outside, "activity": activity}


def activity_level(activity: float, thresholds: tuple[float, float, float]) -> str:
    """按 (static, low, medium) 上界把运动能量离散成等级。"""
    t_static, t_low, t_medium = thresholds
    if activity < t_static:
        return "static"
    if activity < t_low:
        return "low"
    if activity < t_medium:
        return "medium"
    return "high"


def describe(values: list[float]) -> dict:
    """均值/最小/中位/最大；空列表返回全 None。"""
    if not values:
        return {"mean": None, "min": None, "p50": None, "max": None}
    a = np.asarray(values, dtype=np.float64)
    return {
        "mean": round(float(a.mean()), 4),
        "min": round(float(a.min()), 4),
        "p50": round(float(np.median(a)), 4),
        "max": round(float(a.max()), 4),
    }
