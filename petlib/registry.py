"""注册表工厂：create(kind, name, **cfg)。

实现模块在 create() 时才 import（懒加载）——保证 petlib 基础层零重依赖。
新增实现 = 在对应包下写模块 + @register 装饰器（或手动注册）。
"""
from __future__ import annotations

import importlib

_REGISTRIES: dict[str, dict[str, type]] = {"detector": {}, "tracker": {}, "keypoints": {}}

_MODULE_MAP = {
    "detector": {
        "grounding_dino": "petlib.detection.grounding_dino",
    },
    "tracker": {
        "byte_track": "petlib.tracking.byte_track",
        "oc_sort": "petlib.tracking.oc_sort",
        "bot_sort": "petlib.tracking.bot_sort",
        "deep_sort": "petlib.tracking.deep_sort",
    },
    "keypoints": {
        "superanimal": "petlib.keypoints.superanimal",
        "vitpose_ap10k": "petlib.keypoints.vitpose_ap10k",
    },
}


def available(kind: str) -> list[str]:
    """列出某类可用的实现名（import 失败的实现不列出）。"""
    if kind not in _MODULE_MAP:
        raise KeyError(f"unknown kind: {kind} (known: {list(_MODULE_MAP)})")
    out = []
    for name, mod in _MODULE_MAP[kind].items():
        try:
            importlib.import_module(mod)
            out.append(name)
        except ImportError:
            pass
    return sorted(out)


def create(kind: str, name: str, **cfg):
    """工厂：create('tracker', 'byte_track', high_thresh=0.5) → Tracker 实例。"""
    if kind not in _MODULE_MAP:
        raise KeyError(f"unknown kind: {kind}")
    if name not in _MODULE_MAP[kind]:
        raise KeyError(f"unknown {kind} '{name}', available: {available(kind)}")
    mod = importlib.import_module(_MODULE_MAP[kind][name])
    cls_name = {
        "grounding_dino": "GroundingDinoDetector",
        "byte_track": "ByteTrackTracker",
        "oc_sort": "OCSortTracker",
        "bot_sort": "BoTSortTracker",
        "deep_sort": "DeepSortTracker",
        "superanimal": "SuperAnimalExtractor",
        "vitpose_ap10k": "VitPoseAp10kExtractor",
    }[name]
    cls = getattr(mod, cls_name)
    return cls(**cfg)
