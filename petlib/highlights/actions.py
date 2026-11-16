"""行为识别时间轴：读取已有结果，或用 MMAction2 配置滑窗推理（懒加载，需 GPU）。"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

_START_KEYS = ("t_start", "start_sec", "start")
_END_KEYS = ("t_end", "end_sec", "end")


def _pick(rec: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in rec and rec[k] is not None:
            return rec[k]
    raise KeyError(f"missing any of {keys} in {rec}")


def normalize_segment(rec: dict) -> dict:
    seg = {
        "t_start": float(_pick(rec, _START_KEYS)),
        "t_end": float(_pick(rec, _END_KEYS)),
        "label": str(rec["label"]),
        "score": float(rec.get("score", 0.0)),
    }
    top = rec.get("top_k", rec.get("top5"))
    if top:
        seg["top_k"] = [[str(t[0]), round(float(t[1]), 4)] if isinstance(t, (list, tuple))
                        else [str(t["label"]), round(float(t["score"]), 4)] for t in top]
    if seg["t_end"] <= seg["t_start"]:
        raise ValueError(f"empty segment: {rec}")
    return seg


def load_timeline(path: str | Path) -> list[dict]:
    """读取 JSON 列表 / {"segments": [...]} / JSONL（兼容 live_analyze.py 输出）。"""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        records = data.get("segments", []) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    records = [r for r in records if isinstance(r, dict) and "label" in r]
    return sorted((normalize_segment(r) for r in records), key=lambda s: s["t_start"])


def merge_segments(segments: list[dict], max_gap: float = 0.05) -> list[dict]:
    """相邻且同标签的段合并；分数按时长加权平均，top_k 取最长子段的。"""
    out: list[dict] = []
    for seg in sorted(segments, key=lambda s: s["t_start"]):
        last = out[-1] if out else None
        if last and last["label"] == seg["label"] and seg["t_start"] <= last["t_end"] + max_gap:
            d_last = last["t_end"] - last["t_start"]
            d_seg = seg["t_end"] - seg["t_start"]
            last["score"] = (last["score"] * d_last + seg["score"] * d_seg) / (d_last + d_seg)
            if d_seg > last.get("_longest", d_last) and "top_k" in seg:
                last["top_k"] = seg["top_k"]
                last["_longest"] = d_seg
            last["t_end"] = max(last["t_end"], seg["t_end"])
            last["n_windows"] = last.get("n_windows", 1) + seg.get("n_windows", 1)
        else:
            new = dict(seg)
            new.setdefault("n_windows", 1)
            out.append(new)
    for s in out:
        s.pop("_longest", None)
        s["t_start"] = round(s["t_start"], 3)
        s["t_end"] = round(s["t_end"], 3)
        s["score"] = round(s["score"], 4)
    return out


def mark_review(segments: list[dict], review_score: float = 0.5,
                review_labels: tuple[str, ...] = ("abnormal",)) -> list[dict]:
    """异常类或低置信段标记 needs_cloud_review，附原因。"""
    for s in segments:
        reasons = []
        if s["label"] in review_labels:
            reasons.append("abnormal_class")
        if s["score"] < review_score:
            reasons.append("low_confidence")
        s["needs_cloud_review"] = bool(reasons)
        s["review_reasons"] = reasons
    return segments


def label_at(segments: list[dict], t0: float, t1: float) -> dict | None:
    """与 [t0, t1) 重叠最多的行为段（无重叠返回 None）。"""
    best, best_ov = None, 0.0
    for s in segments:
        ov = min(t1, s["t_end"]) - max(t0, s["t_start"])
        if ov > best_ov:
            best, best_ov = s, ov
    if best is None:
        return None
    return {"label": best["label"], "score": best["score"],
            "needs_cloud_review": best.get("needs_cloud_review", False)}


def sliding_windows(duration: float, window: float, stride: float) -> list[tuple[float, float, float, float]]:
    """返回 [(win_start, win_end, assign_start, assign_end)]。

    推理窗口可重叠；assign 区间是每个窗口“负责”的不重叠时段（以窗口中心为界），
    保证合并后的时间轴不重叠且覆盖 [0, duration]。
    """
    if duration <= 0:
        return []
    if duration <= window:
        return [(0.0, duration, 0.0, duration)]
    n = int(math.floor((duration - window) / stride)) + 1
    starts = [i * stride for i in range(n)]
    if starts[-1] + window < duration - 1e-6:
        starts.append(duration - window)
    centers = [s + window / 2 for s in starts]
    out = []
    for i, s in enumerate(starts):
        a0 = 0.0 if i == 0 else (centers[i - 1] + centers[i]) / 2
        a1 = duration if i == len(starts) - 1 else (centers[i] + centers[i + 1]) / 2
        out.append((s, s + window, a0, a1))
    return out


def _to_prob(scores: np.ndarray) -> np.ndarray:
    if scores.min() >= 0 and abs(scores.sum() - 1.0) < 1e-3:
        return scores
    e = np.exp(scores - scores.max())
    return e / e.sum()


class MMActionWindowRecognizer:
    """v1 七类等 MMAction2 区间模型的滑窗推理。

    使用配置中 test_dataloader 的 pipeline（含 RestrictFrameRange），以
    interval_start/interval_end（1 起、闭区间）限定每个窗口的采样范围。
    """

    name = "mmaction2_window"

    def __init__(self, config: str, checkpoint: str, device: str = "cuda:0",
                 window_sec: float = 4.0, stride_sec: float = 2.0, top_k: int = 3):
        from mmengine.config import Config
        from mmengine.dataset import Compose
        from mmaction.apis import init_recognizer
        from mmaction.utils import register_all_modules

        register_all_modules()
        cfg = Config.fromfile(config)
        self.classes = list(cfg.get("classes") or [])
        self.model = init_recognizer(cfg, checkpoint, device=device)
        self.pipeline = Compose(cfg.test_dataloader.dataset.pipeline)
        self.config = str(config)
        self.checkpoint = str(checkpoint)
        self.window_sec = window_sec
        self.stride_sec = stride_sec
        self.top_k = top_k

    def recognize(self, video: str, fps: float, total_frames: int) -> list[dict]:
        from mmaction.apis import inference_recognizer

        duration = total_frames / fps
        segs = []
        for w0, w1, a0, a1 in sliding_windows(duration, self.window_sec, self.stride_sec):
            f_start = int(round(w0 * fps)) + 1
            f_end = max(f_start, min(total_frames, int(round(w1 * fps))))
            data = dict(filename=str(video), label=-1, start_index=0, modality="RGB",
                        interval_start=f_start, interval_end=f_end, sample_id=f"{f_start}-{f_end}")
            res = inference_recognizer(self.model, data, test_pipeline=self.pipeline)
            prob = _to_prob(res.pred_score.detach().cpu().numpy().astype(np.float64))
            order = np.argsort(-prob)[: self.top_k]
            names = [self.classes[i] if i < len(self.classes) else f"class_{i}" for i in order]
            segs.append({
                "t_start": a0, "t_end": a1, "label": names[0], "score": float(prob[order[0]]),
                "top_k": [[n, round(float(prob[i]), 4)] for n, i in zip(names, order)],
            })
        return segs
