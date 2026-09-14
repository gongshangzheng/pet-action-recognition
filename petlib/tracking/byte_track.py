"""ByteTrack 适配实现（简化重实现）：两级关联（高/低置信度）。"""
from __future__ import annotations

import numpy as np

from petlib.schemas import Detection, Track, TrackPoint
from petlib.tracking.base import Tracker
from petlib.tracking.sort_core import KalmanBoxTracker, associate


class ByteTrackTracker(Tracker):
    """ByteTrack 思路：高置信度检测先关联，低置信度检测补偿被遮挡轨迹。

    简化说明：自研 SORT 核心（Kalman+匈牙利），未含官方全部工程细节；
    选型实验（§2）在同一接口下公平对比。
    """

    name = "byte_track"

    def __init__(self, high_thresh: float = 0.5, low_thresh: float = 0.1,
                 iou_threshold: float = 0.3, max_lost: int = 30, **_):
        self.high = high_thresh
        self.low = low_thresh
        self.iou_thr = iou_threshold
        self.max_lost = max_lost
        self.tracks: list[KalmanBoxTracker] = []
        self._hist: dict[int, list[TrackPoint]] = {}

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        highs = [d for d in detections if d.conf >= self.high]
        lows = [d for d in detections if self.low <= d.conf < self.high]

        for t in self.tracks:
            t.predict()

        t_boxes = np.array([t.box for t in self.tracks]) if self.tracks else np.zeros((0, 4))
        h_boxes = np.array([d.box for d in highs]) if highs else np.zeros((0, 4))
        matches, ut, ud = associate(t_boxes, h_boxes, self.iou_thr)
        for ti, di in matches:
            self.tracks[ti].update(np.array(highs[di].box), highs[di].conf)

        # 二级：未匹配轨迹 × 低置信度
        if ut and lows:
            t_boxes2 = np.array([self.tracks[ti].box for ti in ut])
            l_boxes = np.array([d.box for d in lows]) if lows else np.zeros((0, 4))
            m2, ut2, ud2 = associate(t_boxes2, l_boxes, 0.5)
            for ti_local, di in m2:
                self.tracks[ut[ti_local]].update(np.array(lows[di].box), lows[di].conf)
            ud = [d for d in ud if d not in ud2]
            ut = [ti for ti in ut if ti not in [ut[ti_l] for ti_l in m2]]

        # 未匹配高置信度 → 新轨迹
        for di in ud:
            t = KalmanBoxTracker(np.array(highs[di].box), highs[di].conf)
            self.tracks.append(t)

        # 超时轨迹移除
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_lost]

        return self._active(frame_idx)

    def _active(self, frame_idx: int) -> list[Track]:
        out = []
        for t in self.tracks:
            if t.time_since_update == 0:
                b = t.box
                hist = self._hist.setdefault(t.id, [])
                if not hist or hist[-1].frame != frame_idx:
                    hist.append(TrackPoint(frame_idx, tuple(float(v) for v in b), t.conf))
                out.append(Track(t.id, hist))
        return out

    def finalize(self) -> list[Track]:
        out = []
        for t in self.tracks:
            out.append(Track(t.id, self._hist.get(t.id, [])))
        return out
