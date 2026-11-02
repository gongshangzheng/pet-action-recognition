"""`pet.highlight.v1` 上报载荷、确定性 event_id、本地 outbox；以及单视频端到端入口。

本模块不做任何网络上传（云端接收/判断不在本 change 范围）。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from petlib.highlights.actions import mark_review, merge_segments
from petlib.highlights.aggregate import (HighlightConfig, analysis_size, analyze_samples, build_windows,
                                         iter_video_samples, probe_video, sample_step, summarize)
from petlib.highlights.sources import FaceSource, PetSource

SCHEMA = "pet.highlight.v1"
REPO = Path(__file__).resolve().parents[2]


def code_version() -> dict:
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                             timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "petlib/highlights",
                                "scripts/extract_highlight_features.py"], cwd=REPO,
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return {"git_head": rev or None, "highlights_dirty": bool(dirty)}
    except (OSError, subprocess.SubprocessError):
        return {"git_head": None, "highlights_dirty": None}


def make_event_id(identity: dict) -> str:
    blob = json.dumps(identity, sort_keys=True, ensure_ascii=False, default=str)
    return "hl-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def write_outbox(payload: dict, outbox: str | os.PathLike) -> tuple[Path, bool]:
    """原子写入 <outbox>/<event_id>.json；已存在则不覆盖。返回 (路径, 是否新写入)。"""
    d = Path(outbox)
    d.mkdir(parents=True, exist_ok=True)
    final = d / f"{payload['event_id']}.json"
    if final.exists():
        return final, False
    tmp = d / f".{payload['event_id']}.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        if final.exists():  # 并发写入时以先到者为准
            return final, False
        os.replace(tmp, final)
    finally:
        if tmp.exists():
            tmp.unlink()
    return final, True


def extract_highlights(video: str, pet_source: PetSource, face_source: FaceSource,
                       cfg: HighlightConfig | None = None, *, behavior: list[dict] | None = None,
                       behavior_source: dict | None = None, recognizer=None,
                       review_score: float = 0.5, device_id: str | None = None,
                       camera_id: str | None = None, start_time: str | None = None,
                       include_samples: bool = False) -> dict:
    """单视频 → `pet.highlight.v1` 载荷（dict）。

    behavior：已有时间轴（normalize 后的段列表）；recognizer：带 recognize(video, fps, frames)
    的对象（如 MMActionWindowRecognizer）。二者都没有时 behavior.source = none。
    """
    cfg = cfg or HighlightConfig()
    meta = probe_video(video)
    size = analysis_size(meta["width"], meta["height"], cfg.analysis_width)
    step = sample_step(meta["fps"], cfg.analysis_fps)
    pet_source.configure((meta["width"], meta["height"]), size)
    samples = analyze_samples(iter_video_samples(video, step, size), meta["fps"], step,
                              pet_source, face_source, cfg)
    if not samples:
        raise RuntimeError(f"no frames decoded from {video}")
    frames = max(meta["frames"], samples[-1].frame + 1)
    duration = frames / meta["fps"]
    dt = step / meta["fps"]

    if recognizer is not None:
        raw = recognizer.recognize(video, meta["fps"], frames)
        behavior_source = behavior_source or {
            "source": recognizer.name, "config": getattr(recognizer, "config", None),
            "checkpoint": getattr(recognizer, "checkpoint", None),
            "window_sec": getattr(recognizer, "window_sec", None),
            "stride_sec": getattr(recognizer, "stride_sec", None)}
    else:
        raw = behavior or []
    behavior_segments = mark_review(merge_segments(raw), review_score=review_score) if raw else []
    if behavior_source is None:
        behavior_source = {"source": "timeline_json" if raw else "none"}

    summary, segments = summarize(samples, dt, duration, cfg)
    windows = build_windows(samples, duration, cfg, behavior_segments)

    pet_info = {"source": pet_source.name}
    if hasattr(pet_source, "weights"):
        pet_info["weights"] = pet_source.weights
    face_info = {"source": face_source.name}
    if hasattr(face_source, "cascade_path"):
        face_info["cascade"] = Path(face_source.cascade_path).name
    analysis = {
        "analysis_fps": round(meta["fps"] / step, 4), "sample_step": step,
        "analysis_size": list(size), "area_source": pet_source.area_source,
        "pet": pet_info, "face": face_info, "behavior": behavior_source,
        "review_score": review_score, "config": cfg.to_dict(),
        "thresholds_calibrated": False, "code": code_version(),
    }
    source = {"video": str(video), "file_name": Path(video).name, "fps": meta["fps"],
              "frames": frames, "width": meta["width"], "height": meta["height"],
              "duration_sec": round(duration, 3), "start_time": start_time}
    identity = {"video": str(Path(video).resolve()), "start_time": start_time, "frames": frames,
                "fps": meta["fps"], "device_id": device_id, "camera_id": camera_id,
                "config": cfg.to_dict(), "pet": pet_info, "face": face_info,
                "behavior": behavior_source, "review_score": review_score}
    payload = {
        "schema": SCHEMA,
        "event_id": make_event_id(identity),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "device": {"device_id": device_id, "camera_id": camera_id},
        "source": source,
        "analysis": analysis,
        "summary": summary,
        "segments": segments,
        "windows": windows,
        "behavior": {"source": behavior_source.get("source"), "segments": behavior_segments,
                     "needs_cloud_review": any(s["needs_cloud_review"] for s in behavior_segments)},
        "cloud_judgement": None,
    }
    if include_samples:
        payload["samples"] = [{k: (round(v, 4) if isinstance(v, float) else v)
                               for k, v in asdict(s).items()} for s in samples]
    return payload
