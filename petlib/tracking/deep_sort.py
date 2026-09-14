"""DeepOcSort：boxmot 官方级实现（DeepSORT 外观 + OC-SORT 观测中心思想）。"""
from __future__ import annotations

from boxmot import DeepOcSort

from petlib.tracking.boxmot_base import BoxMotAdapter


class DeepSortTracker(BoxMotAdapter):
    name = "deep_sort"

    def _build(self, cfg: dict):
        params = {k: cfg[k] for k in
                  ("delta_t", "inertia", "w_association_emb", "alpha_fixed_emb")
                  if k in cfg}
        return DeepOcSort(**params)
