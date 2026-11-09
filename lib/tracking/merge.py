"""轨迹级时序合并（multi-pet-sort-tracking 3.x 补充机制）。

设计意图（用户要求）：同一只动物可能被检测间隙切成多段——前一段结束、后一段
在几乎同一个位置开始。本模块按「时序相邻 + 位置一致」把它们并回一条轨迹。

**已知风险（实测）**：位置重合的间隙型分割，在我们语料里主要是**静态误检**
（狗粮袋上印刷的金毛）而非真动物。合并它们会让误检轨迹更"长寿"。因此本功能
默认关闭，启用时逐条记录合并证据，供人工复核。
"""
from __future__ import annotations

from lib.schemas import Track, TrackPoint

DEFAULT_GAP_ANCHORS = 0      # 0 = 关闭
DEFAULT_IOS_MIN = 0.8


def _ios(a, b) -> float:
    """交集 / 较小框面积：包含关系下接近 1，IoU 会被大框稀释。"""
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / min(area_a, area_b)


def merge_temporal(
    tracks: list[Track],
    sample_stride: int,
    gap_anchors: int = DEFAULT_GAP_ANCHORS,
    ios_min: float = DEFAULT_IOS_MIN,
) -> tuple[list[Track], list[dict]]:
    """把「前一段结束 + 间隙内后一段在几乎同位置开始」的轨迹并成一条。

    gap_anchors <= 0 时原样返回（默认关闭）。合并保留较早轨迹的 id。
    返回 (合并后的轨迹, 合并日志)。
    """
    if gap_anchors <= 0 or len(tracks) < 2:
        return tracks, []

    ordered = sorted(tracks, key=lambda t: (t.boxes[0].frame, t.track_id))
    kept: list[Track] = []
    log: list[dict] = []

    for cand in ordered:
        target = None
        for k in kept:
            if not k.boxes or not cand.boxes:
                continue
            if k.last_frame() >= cand.boxes[0].frame:
                continue  # 要求严格先后，不处理共存
            gap = (cand.boxes[0].frame - k.last_frame()) // max(1, sample_stride)
            if gap > gap_anchors:
                continue
            ios = _ios(k.last_box(), cand.boxes[0].box)
            if ios < ios_min:
                continue
            target = (k, gap, ios)
            break

        if target is None:
            kept.append(cand)
            continue

        host, gap, ios = target
        merged_boxes = host.boxes + cand.boxes
        log.append(
            {
                "kept_track_id": host.track_id,
                "merged_track_id": cand.track_id,
                "gap_anchors": int(gap),
                "ios": round(float(ios), 4),
                "kept_last_frame": host.last_frame(),
                "merged_first_frame": cand.boxes[0].frame,
            }
        )
        replacement = Track(host.track_id, merged_boxes)
        kept = [replacement if k is host else k for k in kept]

    return kept, log


def points_of(track: Track) -> list[TrackPoint]:
    return track.boxes


# design 4.14：不能稳定存在的轨迹一律放弃（不合并、不补全）
DEFAULT_MIN_STABLE_ANCHORS = 5
DEFAULT_MIN_COVERAGE = 0.6


def filter_stable(
    tracks: list[Track],
    sample_stride: int,
    min_anchors: int = DEFAULT_MIN_STABLE_ANCHORS,
    min_coverage: float = DEFAULT_MIN_COVERAGE,
) -> tuple[list[Track], list[dict]]:
    """丢弃「不能稳定存在」的轨迹：锚点数太少，或跨度内覆盖率太低（闪烁）。

    min_anchors <= 0 时原样返回（关闭过滤）。每条被丢弃的轨迹都记原因，不静默删。
    """
    if min_anchors <= 0:
        return tracks, []

    kept: list[Track] = []
    dropped: list[dict] = []
    for t in tracks:
        if not t.boxes:
            dropped.append({"track_id": t.track_id, "reason": "empty"})
            continue
        span = (t.last_frame() - t.boxes[0].frame) // max(1, sample_stride) + 1
        coverage = len(t.boxes) / span if span else 0.0
        reasons = []
        if len(t.boxes) < min_anchors:
            reasons.append("too_few_anchors")
        if coverage < min_coverage:
            reasons.append("low_coverage")
        if reasons:
            dropped.append(
                {
                    "track_id": t.track_id,
                    "n_anchors": len(t.boxes),
                    "span_anchors": span,
                    "coverage": round(coverage, 4),
                    "first_frame": t.boxes[0].frame,
                    "last_frame": t.last_frame(),
                    "reason": "+".join(reasons),
                }
            )
        else:
            kept.append(t)
    return kept, dropped
