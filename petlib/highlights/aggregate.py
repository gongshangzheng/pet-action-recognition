"""采样循环 → 逐采样指标 → 窗口汇总 / 时长 / 连续段。

端侧只采集指标，不做亮点筛选（由云端判断）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Iterator

import numpy as np

from petlib.highlights import metrics as M
from petlib.highlights.actions import label_at
from petlib.highlights.sources import FaceSource, NoPetSource, PetSource


@dataclass
class HighlightConfig:
    analysis_fps: float = 5.0
    analysis_width: int = 960
    window_sec: float = 1.0
    body_large_ratio: float = 0.05
    activity_thresholds: tuple[float, float, float] = (0.01, 0.03, 0.08)
    gap_fill_sec: float = 0.6
    min_segment_sec: float = 0.4
    region_expand: float = 0.1

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: list(v) if isinstance(v, tuple) else v for k, v in d.items()}


@dataclass
class Sample:
    frame: int
    t: float
    brightness: float
    contrast: float
    contrast_spread: float
    n_pets: int = 0
    body_ratio: float = 0.0
    activity: float | None = None  # 首个采样点无前帧 → None
    motion_inside: float | None = None
    motion_outside: float | None = None
    displacement: float | None = None  # 画面对角线 / 秒
    n_faces: int = 0
    face_ratio: float = 0.0
    face_body_ratio: float | None = None
    pet_boxes: list = field(default_factory=list)
    face_boxes: list = field(default_factory=list)

    @property
    def present(self) -> bool:
        return self.n_pets > 0

    @property
    def face(self) -> bool:
        return self.n_faces > 0


# ── 视频读取 ─────────────────────────────────────────────────────────────

def probe_video(path: str) -> dict:
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    meta = {
        "fps": float(cap.get(cv2.CAP_PROP_FPS) or 0.0),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    if meta["fps"] <= 0:
        raise RuntimeError(f"invalid fps for {path}")
    return meta


def analysis_size(width: int, height: int, target_width: int) -> tuple[int, int]:
    if target_width <= 0 or width <= target_width:
        return width, height
    s = target_width / width
    return target_width, max(1, int(round(height * s)))


def sample_step(fps: float, analysis_fps: float) -> int:
    return max(1, int(round(fps / analysis_fps))) if analysis_fps > 0 else 1


def iter_video_samples(path: str, step: int, size: tuple[int, int]) -> Iterator[tuple[int, np.ndarray]]:
    """按步长跳帧读取，返回 (原帧号, 缩放到分析分辨率的 BGR 帧)。"""
    import cv2

    cap = cv2.VideoCapture(str(path))
    idx = 0
    try:
        while True:
            if idx % step == 0:
                ok, frame = cap.read()
                if not ok:
                    break
                if (frame.shape[1], frame.shape[0]) != size:
                    frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
                yield idx, frame
            else:
                if not cap.grab():
                    break
            idx += 1
    finally:
        cap.release()


# ── 逐采样分析 ───────────────────────────────────────────────────────────

def analyze_samples(frames: Iterable[tuple[int, np.ndarray]], fps: float, step: int,
                    pet_source: PetSource, face_source: FaceSource,
                    cfg: HighlightConfig) -> list[Sample]:
    dt = step / fps
    has_pet_source = not isinstance(pet_source, NoPetSource)
    out: list[Sample] = []
    prev_y = prev_region = prev_c = None
    for idx, frame in frames:
        h, w = frame.shape[:2]
        diag = float(np.hypot(w, h))
        y = M.luma(frame)
        s = Sample(frame=idx, t=round(idx / fps, 4), brightness=M.brightness(y),
                   contrast=M.contrast_rms(y), contrast_spread=M.contrast_spread(y))

        pets = pet_source.observe(frame, idx)
        boxes = [p.box for p in pets]
        if pets:
            body = np.zeros((h, w), dtype=bool)
            for p in pets:
                body |= p.mask if p.mask is not None else M.boxes_mask([p.box], (h, w))
            region = M.boxes_mask([M.expand_box(b, cfg.region_expand) for b in boxes], (h, w)) | body
        else:
            body = region = None
        s.n_pets = len(pets)
        s.body_ratio = M.area_ratio(body) if body is not None else 0.0
        s.pet_boxes = [[round(v, 1) for v in b] for b in boxes]

        if prev_y is not None:
            union = None
            if region is not None and prev_region is not None:
                union = region | prev_region
            elif region is not None or prev_region is not None:
                union = region if region is not None else prev_region
            if union is not None:
                me = M.motion_energy(prev_y, y, union)
                s.activity, s.motion_inside, s.motion_outside = me["activity"], me["inside"], me["outside"]
            else:
                s.activity = 0.0
            c = M.centroid(body) if body is not None else None
            if c is not None and prev_c is not None:
                s.displacement = float(np.hypot(c[0] - prev_c[0], c[1] - prev_c[1]) / diag / dt)

        faces = face_source.detect(frame, boxes if has_pet_source else None)
        if faces:
            fmask = M.boxes_mask([f.box for f in faces], (h, w))
            s.n_faces = len(faces)
            s.face_ratio = M.area_ratio(fmask)
            if s.body_ratio > 0:
                s.face_body_ratio = s.face_ratio / s.body_ratio
            s.face_boxes = [[round(v, 1) for v in f.box] for f in faces]

        out.append(s)
        prev_y, prev_region = y, region
        prev_c = M.centroid(body) if body is not None else None
    return out


# ── 时长与连续段 ─────────────────────────────────────────────────────────

def flags_to_segments(times: list[float], flags: list[bool], dt: float,
                      gap_fill: float, min_len: float, end_time: float | None = None) -> list[list[float]]:
    """连续 True 的采样点 → [t_start, t_end)；先填补短间隔，再丢弃过短段。"""
    raw: list[list[float]] = []
    for t, f in zip(times, flags):
        if not f:
            continue
        t_end = t + dt if end_time is None else min(t + dt, end_time)
        if raw and t <= raw[-1][1] + 1e-6:
            raw[-1][1] = t_end
        else:
            raw.append([t, t_end])
    merged: list[list[float]] = []
    for seg in raw:
        if merged and seg[0] - merged[-1][1] <= gap_fill + 1e-6:
            merged[-1][1] = seg[1]
        else:
            merged.append(list(seg))
    return [[round(a, 3), round(b, 3)] for a, b in merged if b - a >= min_len - 1e-6]


def total_duration(segments: list[list[float]]) -> float:
    return round(sum(b - a for a, b in segments), 3)


# ── 汇总 ─────────────────────────────────────────────────────────────────

def summarize(samples: list[Sample], dt: float, duration: float, cfg: HighlightConfig) -> tuple[dict, dict]:
    times = [s.t for s in samples]
    seg_kw = dict(dt=dt, gap_fill=cfg.gap_fill_sec, min_len=cfg.min_segment_sec, end_time=duration)
    segments = {
        "pet_visible": flags_to_segments(times, [s.present for s in samples], **seg_kw),
        "body_large": flags_to_segments(times, [s.body_ratio >= cfg.body_large_ratio for s in samples], **seg_kw),
        "face_exposed": flags_to_segments(times, [s.face for s in samples], **seg_kw),
    }
    present = [s for s in samples if s.present]
    acts = [s.activity for s in present if s.activity is not None]
    levels: dict[str, float] = {"static": 0.0, "low": 0.0, "medium": 0.0, "high": 0.0}
    for a in acts:
        levels[M.activity_level(a, cfg.activity_thresholds)] += dt
    visible_sec = total_duration(segments["pet_visible"])
    face_sec = total_duration(segments["face_exposed"])
    summary = {
        "duration_sec": round(duration, 3),
        "samples": len(samples),
        "brightness": M.describe([s.brightness for s in samples]),
        "contrast_rms": M.describe([s.contrast for s in samples]),
        "contrast_spread": M.describe([s.contrast_spread for s in samples]),
        "pet_visible_sec": visible_sec,
        "pet_visible_ratio": round(visible_sec / duration, 4) if duration > 0 else 0.0,
        "max_pets": max((s.n_pets for s in samples), default=0),
        "body_area_ratio": M.describe([s.body_ratio for s in present]),
        "body_large_sec": total_duration(segments["body_large"]),
        "activity": M.describe(acts),
        "displacement": M.describe([s.displacement for s in present if s.displacement is not None]),
        "activity_level_sec": {k: round(v, 3) for k, v in levels.items()},
        "face_exposed_sec": face_sec,
        "face_exposed_ratio_of_visible": round(face_sec / visible_sec, 4) if visible_sec > 0 else 0.0,
        "face_area_ratio": M.describe([s.face_ratio for s in samples if s.face]),
        "face_body_ratio": M.describe([s.face_body_ratio for s in samples if s.face_body_ratio is not None]),
    }
    return summary, segments


def _mean(vals: list[float]) -> float | None:
    return round(float(np.mean(vals)), 4) if vals else None


def build_windows(samples: list[Sample], duration: float, cfg: HighlightConfig,
                  behavior: list[dict] | None = None) -> list[dict]:
    out = []
    n = max(1, int(np.ceil(duration / cfg.window_sec - 1e-9)))
    for i in range(n):
        w0 = i * cfg.window_sec
        w1 = min(duration, w0 + cfg.window_sec)
        ss = [s for s in samples if w0 <= s.t < w1]
        if not ss:
            continue
        present = [s for s in ss if s.present]
        acts = [s.activity for s in present if s.activity is not None]
        act_mean = _mean(acts)
        win = {
            "t_start": round(w0, 3), "t_end": round(w1, 3), "samples": len(ss),
            "brightness": _mean([s.brightness for s in ss]),
            "contrast_rms": _mean([s.contrast for s in ss]),
            "contrast_spread": _mean([s.contrast_spread for s in ss]),
            "pet_present_ratio": round(len(present) / len(ss), 4),
            "max_pets": max(s.n_pets for s in ss),
            "body_area_ratio_mean": _mean([s.body_ratio for s in present]),
            "body_area_ratio_max": round(max((s.body_ratio for s in ss), default=0.0), 4),
            "activity_mean": act_mean,
            "activity_max": round(max(acts), 4) if acts else None,
            "activity_level": M.activity_level(act_mean, cfg.activity_thresholds) if act_mean is not None else None,
            "face_exposed_ratio": round(sum(s.face for s in ss) / len(ss), 4),
            "face_area_ratio_max": round(max(s.face_ratio for s in ss), 4),
            "action": label_at(behavior, w0, w1) if behavior else None,
        }
        out.append(win)
    return out

