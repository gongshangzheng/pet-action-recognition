"""读取 cat-crop-detection-v2 检测缓存，组装逐锚点检测序列。

供多宠物跟踪（multi-pet-sort-tracking）消费：把每个锚点的
cat_candidates / dog_candidates 还原成 list[Detection]，帧序单调递增。
锚点数校验内建：与 frame % sample_stride == 0 的应得帧数不一致时抛错。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from petlib.schemas import Detection

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


def expected_anchor_count(decoded_frames: int, sample_stride: int) -> int:
    """frame % sample_stride == 0 的帧数（0 起、decoded_frames 不含）。"""
    return len(range(0, decoded_frames, sample_stride))


def load_anchor_sequence(path: str | Path) -> AnchorSequence:
    """读一份检测缓存 JSON，校验锚点数后返回逐锚点检测序列。"""
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
    for f in frames:
        state = anchors[str(f)]
        row: list[Detection] = []
        for key in ("cat_candidates", "dog_candidates"):
            for cand in state[key]:
                row.append(
                    Detection(
                        frame=f,
                        box=tuple(float(v) for v in cand["box"]),
                        conf=float(cand["confidence"]),
                        cls=cand["class"],
                    )
                )
        detections.append(row)
    return AnchorSequence(
        video=payload["video"],
        sample_stride=stride,
        frames=frames,
        detections=detections,
        source_sha256=payload["source_sha256"],
        fingerprint=payload["fingerprint"],
    )
