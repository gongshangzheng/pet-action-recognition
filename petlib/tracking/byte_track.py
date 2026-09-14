"""ByteTrack：boxmot 官方级实现（两级关联，不丢低分检测）。"""
from __future__ import annotations

from boxmot import ByteTrack

from petlib.tracking.boxmot_base import BoxMotAdapter


class ByteTrackTracker(BoxMotAdapter):
    name = "byte_track"

    def _build(self, cfg: dict):
        params = {k: cfg[k] for k in
                  ("min_conf", "track_thresh", "match_thresh", "track_buffer", "frame_rate")
                  if k in cfg}
        return ByteTrack(**params)
