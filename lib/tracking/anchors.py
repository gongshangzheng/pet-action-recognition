"""读取 cat-crop-detection-v2 检测缓存，组装逐锚点检测序列。

供多宠物跟踪（multi-pet-sort-tracking）消费：把每个锚点的
cat_candidates / dog_candidates 还原成 list[Detection]，帧序单调递增。
锚点数校验内建：与 frame % sample_stride == 0 的应得帧数不一致时抛错。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from lib.schemas import Detection

DETECTION_CACHE_SCHEMA = "cat-crop-detection-v2"


@dataclass
class AnchorSequence:
    """一段视频的逐锚点检测流。"""

    video: str
    sample_stride: int
    frames: list[int]
    detections: list[list[Detection]]
    source_sha256: str
    fingerprint: dict
    dedup_log: list[dict] = field(default_factory=list)
    frame_size: tuple[int, int] = (0, 0)


DEDUP_IOS_MIN = 0.80


def _ios(a, b) -> float:
    """交集 / 较小框面积。包含关系下接近 1，而 IoU 会被大框稀释。"""
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / min(area_a, area_b)


def dedup_nested(detections: list[Detection], frame: int) -> tuple[list[Detection], list[dict]]:
    """嵌套重复去重（design 4.11）：同一帧内 IoS ≥ 0.80 视为同一目标，保留置信度高者。

    跨物种也去重：实测中位段 frames 165/185 的同一只猫被分别标成 cat 与 dog，
    两张列表互不比较，类内去重清不掉。每次删除都记日志，便于事后核对有无误删真动物。
    """
    ordered = sorted(detections, key=lambda d: d.conf, reverse=True)
    kept: list[Detection] = []
    log: list[dict] = []
    for cand in ordered:
        dup = next((k for k in kept if _ios(k.box, cand.box) >= DEDUP_IOS_MIN), None)
        if dup is None:
            kept.append(cand)
            continue
        log.append(
            {
                "frame": frame,
                "dropped_class": cand.cls,
                "dropped_box": [round(float(v), 1) for v in cand.box],
                "dropped_conf": round(float(cand.conf), 4),
                "kept_class": dup.cls,
                "kept_box": [round(float(v), 1) for v in dup.box],
                "kept_conf": round(float(dup.conf), 4),
                "ios": round(_ios(dup.box, cand.box), 4),
            }
        )
    return kept, log


def expected_anchor_count(decoded_frames: int, sample_stride: int) -> int:
    """frame % sample_stride == 0 的帧数（0 起、decoded_frames 不含）。"""
    return len(range(0, decoded_frames, sample_stride))


def load_anchor_sequence(path: str | Path, apply_dedup: bool = True) -> AnchorSequence:
    """读一份检测缓存 JSON，校验锚点数后返回逐锚点检测序列。

    apply_dedup=False 用于对照臂：align 旧数据，不应用 design 4.11 的 IoS 去重。
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != DETECTION_CACHE_SCHEMA:
        raise ValueError(
            f"{path}: schema {payload.get('schema')!r} != {DETECTION_CACHE_SCHEMA!r}"
        )
    stride = payload["sample_stride"]
    anchors = payload["anchors"]
    frames = sorted(int(f) for f in anchors)
    if frames != list(range(0, payload["decoded_frames"], stride)):
        raise ValueError(
            f"{path}: anchor frames != frame % {stride} == 0 sequence "
            f"({len(frames)} anchors vs decoded {payload['decoded_frames']})"
        )
    detections: list[list[Detection]] = []
    dedup_log: list[dict] = []
    for f in frames:
        state = anchors[str(f)]
        row: list[Detection] = []
        for key in ("cat_candidates", "dog_candidates"):
            for cand in state[key]:
                x1, y1, x2, y2 = (float(v) for v in cand["box"])
                row.append(
                    Detection(
                        frame=f,
                        box=(x1, y1, x2, y2),
                        conf=float(cand["confidence"]),
                        cls=cand["class"],
                    )
                )
        kept, dropped = dedup_nested(row, f) if apply_dedup else (row, [])
        dedup_log.extend(dropped)
        detections.append(kept)
    return AnchorSequence(
        video=payload["video"],
        sample_stride=stride,
        frames=frames,
        detections=detections,
        source_sha256=payload["source_sha256"],
        fingerprint=payload["fingerprint"],
        dedup_log=dedup_log,
        frame_size=(int(payload["properties"]["width"]), int(payload["properties"]["height"])),
    )
