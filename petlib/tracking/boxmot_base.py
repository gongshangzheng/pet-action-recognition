"""BoxMOT 统一适配基类：包装 boxmot 库（官方级多目标跟踪实现）。

真实现来源：boxmot 25.x（ByteTrack/OcSort/BotSort/DeepOcSort 官方级算法）。
本基类只做三件事：Detection→(N,6) 数组转换、逐帧结果→Track 历史维护、
finalize 全量输出。子类只需实现 _build(cfg) 返回 boxmot 跟踪器实例。
"""
from __future__ import annotations

import numpy as np

from petlib.schemas import Detection, Track, TrackPoint
from petlib.tracking.base import Tracker


class BoxMotAdapter(Tracker):
    name = "boxmot"

    def __init__(self, **cfg):
        self._impl = self._build(cfg)
        self._hist: dict[int, list[TrackPoint]] = {}

    def _build(self, cfg: dict):
        """子类返回 boxmot 跟踪器实例。"""
        raise NotImplementedError

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        if detections:
            arr = np.array(
                [[*d.box, d.conf, 0.0] for d in detections], dtype=np.float32)
        else:
            arr = np.zeros((0, 6), dtype=np.float32)
        out = self._impl.update(arr, None)  # boxmot: (N,8) [x1,y1,x2,y2,id,conf,cls,det]
        out = np.asarray(out).reshape(-1, 8) if out is not None and out.size else np.zeros((0, 8))
        frame_tracks = []
        for row in out:
            tid = int(row[4])
            hist = self._hist.setdefault(tid, [])
            point = TrackPoint(frame_idx, tuple(float(v) for v in row[:4]), float(row[5]))
            if not hist or hist[-1].frame != frame_idx:
                hist.append(point)
            frame_tracks.append(Track(tid, hist))
        return frame_tracks

    def finalize(self) -> list[Track]:
        return [Track(tid, hist) for tid, hist in sorted(self._hist.items())]
