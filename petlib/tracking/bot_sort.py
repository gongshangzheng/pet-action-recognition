"""BoT-SORT：boxmot 官方级实现（CMC 相机补偿 + Re-ID 外观融合）。"""
from __future__ import annotations

from boxmot import BotSort

from petlib.tracking.boxmot_base import BoxMotAdapter


class BoTSortTracker(BoxMotAdapter):
    name = "bot_sort"

    def _build(self, cfg: dict):
        params = {k: cfg[k] for k in
                  ("track_high_thresh", "track_low_thresh", "new_track_thresh", "track_buffer")
                  if k in cfg}
        return BotSort(**params)
