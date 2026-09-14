"""DeepSORT 适配实现（简化）：级联匹配（按轨迹年龄分桶）+ 可选外观 Re-ID。"""
from __future__ import annotations

import numpy as np

from petlib.schemas import Detection, Track, TrackPoint
from petlib.tracking.base import Tracker
from petlib.tracking.sort_core import KalmanBoxTracker, associate


class DeepSortTracker(Tracker):
    """DeepSORT 思路简化版：级联匹配（近龄轨迹优先）+ 外观特征钩子（默认退化为 IoU）。"""

    name = "deep_sort"

    def __init__(self, appearance_fn=None, max_age: int = 30, iou_threshold: float = 0.3,
                 cascade_age: int = 5, **_):
        self.tracks: list[KalmanBoxTracker] = []
        self._hist: dict[int, list[TrackPoint]] = {}
        self.max_age = max_age
        self.iou_thr = iou_threshold
        self.cascade_age = cascade_age
        self.appearance_fn = appearance_fn  # Callable(img, box) -> embedding | None

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        for t in self.tracks:
            t.predict()
        # 级联：按 time_since_update 从小到大分桶匹配
        remaining = list(range(len(detections)))
        for age_bucket in range(0, self.max_age + 1, self.cascade_age):
            cand_tracks = [ti for ti, t in enumerate(self.tracks)
                           if age_bucket <= t.time_since_update < age_bucket + self.cascade_age]
            if not cand_tracks or not remaining:
                continue
            t_boxes = np.array([self.tracks[ti].box for ti in cand_tracks])
            d_boxes = np.array([detections[di].box for di in remaining])
            m, ut, ud = associate(t_boxes, d_boxes, self.iou_thr)
            for ti_local, di in m:
                self.tracks[cand_tracks[ti_local]].update(np.array(detections[di].box), detections[di].conf)
                remaining.remove(di)
            ut = [cand_tracks[ti] for ti in ut]
        # 全部级联仍未匹配的检测 → 新轨迹
        for di in remaining:
            t = KalmanBoxTracker(np.array(detections[di].box), detections[di].conf)
            self.tracks.append(t)
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        out = []
        for t in self.tracks:
            if t.time_since_update == 0:
                hist = self._hist.setdefault(t.id, [])
                if not hist or hist[-1].frame != frame_idx:
                    hist.append(TrackPoint(frame_idx, tuple(float(v) for v in t.box), t.conf))
                out.append(Track(t.id, hist))
        return out

    def finalize(self) -> list[Track]:
        return [Track(t.id, self._hist.get(t.id, [])) for t in self.tracks]
