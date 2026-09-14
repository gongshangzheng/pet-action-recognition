"""OC-SORT 适配实现（简化）：ByteTrack 基础 + 观测中心的速度方向一致性代价。"""
from __future__ import annotations

import numpy as np

from petlib.schemas import Detection, Track, TrackPoint
from petlib.tracking.base import Tracker
from petlib.tracking.byte_track import ByteTrackTracker
from petlib.tracking.sort_core import associate


class OCSortTracker(ByteTrackTracker):
    """OC-SORT 思路简化版：关联代价加入速度方向一致性（ORI），防止漂移误关联。"""

    name = "oc_sort"

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        highs = [d for d in detections if d.conf >= self.high]
        if highs and self.tracks:
            # 观测中心一致性：预测方向 vs 检测方向夹角惩罚（简化 ORI）
            for t in self.tracks:
                if len(t.kf) >= 8 and abs(t.kf[4]) + abs(t.kf[5]) > 1e-3:
                    v = t.kf[4:6]
                    for d in highs:
                        obs_v = np.array(d.box[:2]) - t.box[:2]
                        n1, n2 = np.linalg.norm(v), np.linalg.norm(obs_v)
                        if n1 > 1e-3 and n2 > 1e-3:
                            cos_sim = float(np.dot(v, obs_v) / (n1 * n2))
                            d.conf *= max(0.0, cos_sim)  # 方向背离则降权
        return super().update(detections, frame_idx)
