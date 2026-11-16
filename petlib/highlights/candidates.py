"""端侧亮点参考候选：宠物占比大 + 动作明显（design D9，2026-11-16 修订）。

只依赖 `build_windows` 的 1 秒窗口汇总，可从已有载荷离线重算。端侧只标出参考时间段，
不裁剪、不删除视频；是否采用由云端决定（`cloud_judgement` 不受影响）。

规则（阈值都在 HighlightConfig 里，可在 CLI 覆盖；均为参考值，未经真实数据校准）：
1. 亮点秒：窗口 `body_area_ratio_mean ≥ highlight_area_ratio` 且 `activity_mean ≥ highlight_activity`。
2. 间隔 ≤ highlight_gap_sec 的亮点秒合并成段；核心段短于 highlight_min_sec 丢弃。
3. 核心段过长时只保留得分最高的连续一段，使外扩后不超过 highlight_max_sec。
4. 前后各外扩 highlight_pad_sec（裁到视频范围）；相邻候选的外扩部分可能重叠。
5. 得分 = 0.5·min(1, 占比均值/highlight_area_full) + 0.5·min(1, 活动均值/highlight_activity_full)，
   按核心段内亮点秒计算；按得分降序取前 highlight_top_k 个。
"""
from __future__ import annotations

from collections import Counter

RULE_NAME = "area_motion_v0"
_EPS = 1e-9


def highlight_rule(cfg) -> dict:
    """载荷 `analysis.highlight_rule`：规则名与全部阈值。"""
    return {
        "name": RULE_NAME,
        "area_ratio": cfg.highlight_area_ratio,
        "activity": cfg.highlight_activity,
        "gap_sec": cfg.highlight_gap_sec,
        "min_sec": cfg.highlight_min_sec,
        "pad_sec": cfg.highlight_pad_sec,
        "max_sec": cfg.highlight_max_sec,
        "top_k": cfg.highlight_top_k,
        "area_full": cfg.highlight_area_full,
        "activity_full": cfg.highlight_activity_full,
        "calibrated": False,
    }


def _qualifies(w: dict, cfg) -> bool:
    area, act = w.get("body_area_ratio_mean"), w.get("activity_mean")
    return (area is not None and act is not None
            and area >= cfg.highlight_area_ratio - _EPS and act >= cfg.highlight_activity - _EPS)


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _score(hits: list[dict], cfg) -> tuple[float, float, float]:
    area = _mean([w["body_area_ratio_mean"] for w in hits])
    act = _mean([w["activity_mean"] for w in hits])
    score = 0.5 * min(1.0, area / cfg.highlight_area_full) + 0.5 * min(1.0, act / cfg.highlight_activity_full)
    return score, area, act


def _runs(windows: list[dict], cfg) -> list[list[dict]]:
    """把亮点窗口按间隔合并成若干段（每段是亮点窗口列表，按时间排序）。"""
    hits = sorted((w for w in windows if _qualifies(w, cfg)), key=lambda w: w["t_start"])
    runs: list[list[dict]] = []
    for w in hits:
        if runs and w["t_start"] - runs[-1][-1]["t_end"] <= cfg.highlight_gap_sec + _EPS:
            runs[-1].append(w)
        else:
            runs.append([w])
    return runs


def _best_span(run: list[dict], core_max: float, cfg) -> list[dict]:
    """核心段超长时，取总长 ≤ core_max、得分最高（并列取最早）的连续亮点窗口。"""
    if run[-1]["t_end"] - run[0]["t_start"] <= core_max + _EPS:
        return run
    best, best_score = run[:1], -1.0
    for i in range(len(run)):
        j = i
        while j + 1 < len(run) and run[j + 1]["t_end"] - run[i]["t_start"] <= core_max + _EPS:
            j += 1
        span = run[i:j + 1]
        s = _score(span, cfg)[0]
        if s > best_score + _EPS:
            best, best_score = span, s
    return best


def _overlapping(windows: list[dict], t0: float, t1: float) -> list[dict]:
    return [w for w in windows if w["t_start"] < t1 - _EPS and w["t_end"] > t0 + _EPS]


def _top_action(windows: list[dict]) -> dict | None:
    labels = [w["action"]["label"] for w in windows if w.get("action")]
    if not labels:
        return None
    label, _ = Counter(labels).most_common(1)[0]  # 并列时取最先出现的
    scores = [w["action"]["score"] for w in windows if w.get("action") and w["action"]["label"] == label]
    return {"label": label, "score": round(_mean(scores), 4),
            "needs_cloud_review": any(w["action"].get("needs_cloud_review", False)
                                      for w in windows if w.get("action") and w["action"]["label"] == label)}


def find_candidates(windows: list[dict], duration: float, cfg) -> list[dict]:
    """1 秒窗口 → 亮点参考候选列表（按得分降序，最多 top_k 个；无候选返回空列表）。"""
    core_max = max(cfg.highlight_min_sec, cfg.highlight_max_sec - 2 * cfg.highlight_pad_sec)
    picked = []
    for run in _runs(windows, cfg):
        if run[-1]["t_end"] - run[0]["t_start"] < cfg.highlight_min_sec - _EPS:
            continue
        span = _best_span(run, core_max, cfg)
        core0, core1 = span[0]["t_start"], span[-1]["t_end"]
        t0 = max(0.0, core0 - cfg.highlight_pad_sec)
        t1 = min(duration, core1 + cfg.highlight_pad_sec)
        score, area, act = _score(span, cfg)
        around = _overlapping(windows, t0, t1)
        core_windows = _overlapping(windows, core0, core1)
        face_sec = sum(w.get("face_exposed_ratio", 0.0) * (w["t_end"] - w["t_start"]) for w in around)
        bright = [w["brightness"] for w in around if w.get("brightness") is not None]
        picked.append({
            "t_start": round(t0, 3), "t_end": round(t1, 3), "duration_sec": round(t1 - t0, 3),
            "core_start": round(core0, 3), "core_end": round(core1, 3),
            "highlight_sec": round(sum(w["t_end"] - w["t_start"] for w in span), 3),
            "score": round(score, 4),
            "body_area_ratio_mean": round(area, 4),
            "body_area_ratio_max": round(max(w.get("body_area_ratio_max", 0.0) for w in core_windows), 4),
            "activity_mean": round(act, 4),
            "face_exposed_sec": round(face_sec, 3),
            "brightness_mean": round(_mean(bright), 4) if bright else None,
            "action": _top_action(core_windows),
        })
    picked.sort(key=lambda c: (-c["score"], c["t_start"]))
    out = picked[:max(0, int(cfg.highlight_top_k))]
    for i, c in enumerate(out, 1):
        c["rank"] = i
    return out
