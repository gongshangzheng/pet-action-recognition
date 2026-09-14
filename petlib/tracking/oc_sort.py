"""OC-SORT：boxmot 官方级实现（观测中心三修正）。"""
from __future__ import annotations

from boxmot import OcSort

from petlib.tracking.boxmot_base import BoxMotAdapter


class OCSortTracker(BoxMotAdapter):
    name = "oc_sort"

    def _build(self, cfg: dict):
        params = {k: cfg[k] for k in ("min_conf", "delta_t", "inertia", "use_byte") if k in cfg}
        return OcSort(**params)
