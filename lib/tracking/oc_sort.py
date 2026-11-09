"""OC-SORT：boxmot 官方级实现（观测中心三修正）。

生命周期参数（max_age/min_hits 等）以错点数为单位标定（design 4.7）：
3Hz 错点下 max_age=8 ≈ 2.7s coast，min_hits=2 新轨迹确认。
"""
from __future__ import annotations

from boxmot import OcSort

from lib.tracking.boxmot_base import BoxMotAdapter


class OCSortTracker(BoxMotAdapter):
    name = "oc_sort"

    def _build(self, cfg: dict):
        params = {
            k: cfg[k]
            for k in (
                "min_conf",
                "delta_t",
                "inertia",
                "use_byte",
                "det_thresh",
                "max_age",
                "min_hits",
                "iou_threshold",
            )
            if k in cfg
        }
        return OcSort(**params)
