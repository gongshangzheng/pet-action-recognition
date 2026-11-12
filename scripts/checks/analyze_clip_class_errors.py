#!/usr/bin/env python3
"""把一次片段分类测试的逐样本预测拆成类别级错误分析，并渲染案例素材。

输入是 mmaction2 测试产出的 `test_metrics.json`（含 classes / per_class /
confusion_matrix / predictions）以及同一批渲染片段所在目录。输出三样东西：

1. `per_class.json`：support、预测数、TP/FP/FN、precision/recall/F1（含 95% Wilson 区间），
2. `error_flows.json`：每个真实类别的错误流向，以及「错误流向 activity」的汇总量，
3. `clip_visual_stats.json`：逐片段的亮度/饱和/画面运动描述量（用片段本身算，不依赖标注），
4. `cases.json`：按混淆对挑出的候选案例（作者再从中显式选进报告）。

`media` 子命令把选中的片段渲染成条纹图（image）或 H.264 短片（video）供报告使用。

用法：

    python3 scripts/checks/analyze_clip_class_errors.py stats \
        --metrics results/cat_clip_v9_analysis/test_metrics.json \
        --clips-dir results/cat_clip_v9_analysis/clips \
        --out results/cat_clip_v9_analysis/analysis
    python3 scripts/checks/analyze_clip_class_errors.py cases \
        --analysis results/cat_clip_v9_analysis/analysis \
        --out results/cat_clip_v9_analysis/analysis/cases.json
    python3 scripts/checks/analyze_clip_class_errors.py media \
        --analysis results/cat_clip_v9_analysis/analysis \
        --clips-dir results/cat_clip_v9_analysis/clips \
        --assets-out /tmp/assets --media-out /tmp/media
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lib.videowriter import H264VideoWriter  # noqa: E402

# 采样 10 帧（步长 6，15fps 下间隔 0.4 秒）足够估运动量，又不必解码全部 60 帧。
SAMPLE_STEP = 6
SAMPLE_COUNT = 10
# 16×16 像素的块用来区分「局部爪子动作」与「整体身体移动」。
GRID = 16
# 对照图里每个格子的边长：与训练片段一致，避免放大失真。
TILE_SIZE = 256
# 红外/夜视片段在 HSV 里几乎没有饱和度；阈值取 30 是经验值，见 report 的校准说明。
IR_SAT_THRESHOLD = 30.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="per-class metrics + error flows + clip visual stats")
    p_stats.add_argument("--metrics", type=Path, required=True)
    p_stats.add_argument("--clips-dir", type=Path, required=True)
    p_stats.add_argument("--out", type=Path, required=True)

    p_cases = sub.add_parser("cases", help="pick candidate cases per confusion pair")
    p_cases.add_argument("--analysis", type=Path, required=True, help="stats 输出目录（含 per_class.json）")
    p_cases.add_argument("--metrics", type=Path, required=True)
    p_cases.add_argument("--out", type=Path, required=True)
    p_cases.add_argument("--per-pair", type=int, default=3, help="每个混淆对保留几个候选")
    p_cases.add_argument("--min-conf", type=float, default=0.0, help="只保留置信度不低于该值的错误")

    p_profile = sub.add_parser("profile", help="per-window motion profile of a rendered interval video")
    p_profile.add_argument("--video", type=Path, required=True, help="区间整段渲染出的 mp4")
    p_profile.add_argument("--out", type=Path, required=True, help="输出 json 路径")
    p_profile.add_argument("--bucket", type=float, default=0.5, help="汇总桶宽（秒）")

    p_class = sub.add_parser("class-cases", help="pick one class's correct/wrong clips with their diagnostic numbers")
    p_class.add_argument("--analysis", type=Path, required=True, help="stats 输出目录（含 clip_visual_stats.json）")
    p_class.add_argument("--metrics", type=Path, required=True)
    p_class.add_argument("--label", required=True)
    p_class.add_argument("--correct", type=int, default=6)
    p_class.add_argument("--wrong", type=int, default=6)
    p_class.add_argument("--out", type=Path, required=True)

    p_sheet = sub.add_parser("sheet", help="contact sheet: one representative frame per case, with its numbers")
    p_sheet.add_argument("--cases", type=Path, required=True)
    p_sheet.add_argument("--clips-dir", type=Path, required=True)
    p_sheet.add_argument("--out", type=Path, required=True)
    p_sheet.add_argument("--columns", type=int, default=4)
    p_sheet.add_argument("--frame", type=int, default=30, help="每段取第几帧（1 起）")
    p_sheet.add_argument("--font", default="", help="中文字体路径，默认按候选列表探测")

    p_media = sub.add_parser("media", help="render selected cases to strips / mp4")
    p_media.add_argument("--analysis", type=Path, required=True)
    p_media.add_argument("--clips-dir", type=Path, required=True)
    p_media.add_argument("--assets-out", type=Path, required=True)
    p_media.add_argument("--media-out", type=Path, required=True)
    p_media.add_argument("--select", type=str, default="", help="逗号分隔的 case id，默认渲染全部")
    p_media.add_argument("--cases", type=Path, default=None, help="案例清单，默认 <analysis>/cases.json")
    p_media.add_argument("--fps", type=float, default=15.0)
    return parser.parse_args()


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson 区间（百分比）。小 support 类别不能只看点估计。"""
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, (centre - margin) * 100), min(100.0, (centre + margin) * 100)


def load_json(path: Path, what: str) -> Any:
    """读取 JSON 并在坏输入时给出可定位的失败，而不是抛裸 OSError/JSONDecodeError。"""
    try:
        return json.loads(path.read_text())
    except OSError as error:
        raise SystemExit(f"读不到{what}：{path}（{error}）") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"{what}不是合法 JSON：{path}（{error.msg}）") from error


def load_metrics(path: Path) -> dict[str, Any]:
    data = load_json(path, "测试指标文件")
    if not isinstance(data, dict):
        raise SystemExit(f"{path} 顶层不是对象，不是预期的 test_metrics.json")
    for key in ("classes", "per_class", "confusion_matrix", "predictions"):
        if key not in data:
            raise SystemExit(f"{path} 缺少字段 {key}，不是预期的 test_metrics.json")
    return data


def per_class_table(data: dict[str, Any]) -> list[dict[str, Any]]:
    classes: list[str] = data["classes"]
    preds = data["predictions"]
    matrix = data["confusion_matrix"]
    total = len(preds)
    # 片段不是独立样本：同一标注区间会切出多个 60 帧窗口，且都会进同一个 split。
    # 先按类别收集「区间键」，后面报 support 时同时给区间数。
    intervals_by_label: dict[int, set[str]] = {}
    for prediction in preds:
        parts = prediction["sample_id"].rsplit(":", 2)
        interval_key = f"{parts[-2]}@{parts[0]}" if len(parts) == 3 else prediction["sample_id"]
        intervals_by_label.setdefault(prediction["label"], set()).add(interval_key)
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(classes):
        support = sum(1 for p in preds if p["label"] == index)
        predicted = sum(1 for p in preds if p["predicted"] == index)
        tp = matrix[index][index] if index < len(matrix) else 0
        precision = tp / predicted * 100 if predicted else 0.0
        recall = tp / support * 100 if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        recall_ci = wilson(tp, support)
        precision_ci = wilson(tp, predicted)
        errors = support - tp
        rows.append({
            "label": name,
            "support": support,
            "supportSharePercent": round(support / total * 100, 2) if total else 0.0,
            "predicted": predicted,
            "tp": tp,
            "fp": predicted - tp,
            "fn": errors,
            "distinctIntervals": len(intervals_by_label.get(index, ())),
            "precisionPercent": round(precision, 2),
            "precisionCi95": [round(precision_ci[0], 2), round(precision_ci[1], 2)],
            "recallPercent": round(recall, 2),
            "recallCi95": [round(recall_ci[0], 2), round(recall_ci[1], 2)],
            "f1Percent": round(f1, 2),
        })
    return rows


def error_flows(data: dict[str, Any]) -> dict[str, Any]:
    classes: list[str] = data["classes"]
    matrix = data["confusion_matrix"]
    preds = data["predictions"]
    total = len(preds)
    correct = sum(matrix[i][i] for i in range(len(classes)))
    flows: list[dict[str, Any]] = []
    for true_index, true_name in enumerate(classes):
        row = matrix[true_index]
        support = sum(row)
        destinations = [
            {"label": classes[pred_index], "count": count, "shareOfClassErrorsPercent": 0.0}
            for pred_index, count in enumerate(row) if pred_index != true_index and count
        ]
        errors = support - row[true_index]
        for dest in destinations:
            dest["shareOfClassErrorsPercent"] = round(dest["count"] / errors * 100, 1) if errors else 0.0
        destinations.sort(key=lambda d: -d["count"])
        flows.append({
            "label": true_name,
            "support": support,
            "errors": errors,
            "destinations": destinations,
        })

    activity_index = classes.index("activity") if "activity" in classes else None
    sink: dict[str, Any] = {}
    if activity_index is not None:
        into_activity = [
            {"label": classes[true_index], "count": matrix[true_index][activity_index]}
            for true_index in range(len(classes))
            if true_index != activity_index and matrix[true_index][activity_index]
        ]
        into_activity.sort(key=lambda d: -d["count"])
        total_errors = total - correct
        sink = {
            "totalErrors": total_errors,
            "errorsIntoActivity": sum(d["count"] for d in into_activity),
            "shareOfAllErrorsPercent": round(sum(d["count"] for d in into_activity) / total_errors * 100, 1)
            if total_errors else 0.0,
            "sources": [
                {
                    **entry,
                    "shareOfOwnClassErrorsPercent": round(
                        entry["count"] / next(f["errors"] for f in flows if f["label"] == entry["label"]) * 100, 1
                    ) if next(f["errors"] for f in flows if f["label"] == entry["label"]) else 0.0,
                }
                for entry in into_activity
            ],
            # 「永远判 activity」的 top-1 = activity 的 support 占比，是这条捷径的参照线。
            "alwaysActivityBaselinePercent": round(sum(matrix[activity_index]) / total * 100, 2) if total else 0.0,
        }
    return {"totalSamples": total, "correct": correct, "flows": flows, "activitySink": sink,
            "confusionPairs": confusion_pairs(data)}


def confusion_pairs(data: dict[str, Any], min_count: int = 3) -> list[dict[str, Any]]:
    """列出成规模的混淆对及其置信度：错误的「确定程度」比错误率本身更能说明问题性质。"""
    classes: list[str] = data["classes"]
    matrix = data["confusion_matrix"]
    preds = data["predictions"]
    pairs: list[dict[str, Any]] = []
    for true_index, true_name in enumerate(classes):
        for pred_index, count in enumerate(matrix[true_index]):
            if pred_index == true_index or count < min_count:
                continue
            confidences = sorted(
                max(p["scores"]) for p in preds
                if p["label"] == true_index and p["predicted"] == pred_index
            )
            pairs.append({
                "true": true_name,
                "predicted": classes[pred_index],
                "count": count,
                "medianConfidence": round(statistics.median(confidences), 4),
                "shareWithConfidenceAtLeast80Percent": round(
                    sum(1 for c in confidences if c >= 0.8) / len(confidences) * 100, 1
                ),
            })
    pairs.sort(key=lambda p: -p["count"])
    return pairs


def source_of(sample_id: str) -> str:
    """来源标识 = 文件名里 `__event` 之前的部分（设备/家庭前缀）；没有前缀时归为 no-device。"""
    base = sample_id.rsplit(":", 2)[0]
    return base.split("__event")[0] if "__event" in base else "no-device"


def source_breakdown(data: dict[str, Any]) -> dict[str, Any]:
    """按来源（设备/家庭）拆错误，并做留一来源的敏感情检查。

    类别级指标很容易被单一来源的视角或标注口径拖跑偏，只看全局会误以为「类本身不可分」。
    """
    classes: list[str] = data["classes"]
    preds = data["predictions"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for pred in preds:
        groups.setdefault(source_of(pred["sample_id"]), []).append(pred)

    sources: list[dict[str, Any]] = []
    for name, items in groups.items():
        matrix: dict[tuple[int, int], int] = {}
        for pred in items:
            key = (pred["label"], pred["predicted"])
            matrix[key] = matrix.get(key, 0) + 1
        correct = sum(count for (true_index, pred_index), count in matrix.items() if true_index == pred_index)
        scratching = classes.index("scratching") if "scratching" in classes else None
        sources.append({
            "source": name,
            "n": len(items),
            "errors": len(items) - correct,
            "errorRatePercent": round((len(items) - correct) / len(items) * 100, 1),
            "scratchingSupport": sum(count for (true_index, _), count in matrix.items() if true_index == scratching)
            if scratching is not None else 0,
            "scratchingTp": matrix.get((scratching, scratching), 0) if scratching is not None else 0,
            "scratchingFalsePositives": sum(
                count for (true_index, pred_index), count in matrix.items()
                if scratching is not None and pred_index == scratching and true_index != scratching
            ),
        })
    sources.sort(key=lambda s: -s["errors"])

    leave_one_out: list[dict[str, Any]] = []
    for source in [s["source"] for s in sources if s["n"] >= 10]:
        kept = [p for p in preds if source_of(p["sample_id"]) != source]
        per_class: dict[str, Any] = {}
        for index, name in enumerate(classes):
            support = sum(1 for p in kept if p["label"] == index)
            if not support:
                continue
            tp = sum(1 for p in kept if p["label"] == index and p["predicted"] == index)
            per_class[name] = {"support": support, "recallPercent": round(tp / support * 100, 1)}
        correct = sum(1 for p in kept if p["label"] == p["predicted"])
        leave_one_out.append({
            "excludedSource": source,
            "n": len(kept),
            "top1Percent": round(correct / len(kept) * 100, 2),
            "macroRecallPercent": round(
                statistics.mean([v["recallPercent"] for v in per_class.values() if v["support"] >= 10]), 2
            ),
            "perClassRecall": per_class,
        })
    return {"sources": sources, "leaveOneSourceOut": leave_one_out}


def clip_visual_stats(data: dict[str, Any], clips_dir: Path) -> list[dict[str, Any]]:
    """逐片段算亮度、饱和、整体运动、局部运动占比。不参与训练，只做诊断。"""
    classes: list[str] = data["classes"]
    results: list[dict[str, Any]] = []
    missing = 0
    for pred in data["predictions"]:
        clip = clips_dir / Path(pred["video"]).name
        record: dict[str, Any] = {
            "sample_id": pred["sample_id"],
            "clip": Path(pred["video"]).name,
            "label": classes[pred["label"]],
            "predicted": classes[pred["predicted"]],
            "correct": pred["label"] == pred["predicted"],
            "confidence": round(max(pred["scores"]), 4),
        }
        cap = cv2.VideoCapture(str(clip))
        if not cap.isOpened():
            missing += 1
            cap.release()
            record["missing"] = True
            results.append(record)
            continue
        frames: list[np.ndarray] = []
        index = 0
        while len(frames) < SAMPLE_COUNT:
            ok, frame = cap.read()
            if not ok:
                break
            if index % SAMPLE_STEP == 0:
                frames.append(frame)
            index += 1
        cap.release()
        if len(frames) < 2:
            missing += 1
            record["missing"] = True
            results.append(record)
            continue
        grays = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
        record["lumaMean"] = round(float(np.mean([g.mean() for g in grays])), 2)
        record["contrastMean"] = round(float(np.mean([g.std() for g in grays])), 2)
        record["saturationMean"] = round(
            float(np.mean([cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 1].mean() for frame in frames])), 2
        )
        record["isInfraredLike"] = record["saturationMean"] < IR_SAT_THRESHOLD
        diffs = [cv2.absdiff(grays[i + 1], grays[i]).astype(np.float32) for i in range(len(grays) - 1)]
        record["motionMean"] = round(float(np.mean([d.mean() for d in diffs])), 3)
        # 分块后取高分位 + 活跃块占比：区分「局部爪子动」和「整体身体移动」。
        h, w = grays[0].shape
        bh, bw = h // GRID, w // GRID
        block_p95: list[float] = []
        active_fraction: list[float] = []
        for diff in diffs:
            blocks = diff[: bh * GRID, : bw * GRID].reshape(GRID, bh, GRID, bw).mean(axis=(1, 3))
            block_p95.append(float(np.percentile(blocks, 95)))
            active_fraction.append(float((blocks > max(2.0, blocks.mean())).mean()))
        record["localMotionP95"] = round(float(np.mean(block_p95)), 3)
        record["activeBlockFraction"] = round(float(np.mean(active_fraction)), 3)
        results.append(record)
    if missing:
        print(f"[warn] {missing} 个片段无法解码或被跳过", file=sys.stderr)
    return results


def summarise_visual(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """按真实类聚合亮度/运动/红外占比，并区分判对与判错的片段。"""
    usable = [s for s in stats if not s.get("missing")]
    by_class: dict[str, Any] = {}
    for label in sorted({s["label"] for s in usable}):
        subset = [s for s in usable if s["label"] == label]
        wrong = [s for s in subset if not s["correct"]]
        right = [s for s in subset if s["correct"]]

        def med(items: list[dict[str, Any]], key: str) -> float | None:
            return round(statistics.median([i[key] for i in items]), 3) if items else None

        by_class[label] = {
            "n": len(subset),
            "irLikeSharePercent": round(sum(1 for s in subset if s["isInfraredLike"]) / len(subset) * 100, 1),
            "medianLuma": med(subset, "lumaMean"),
            "medianContrast": med(subset, "contrastMean"),
            "medianMotion": med(subset, "motionMean"),
            "medianLocalMotionP95": med(subset, "localMotionP95"),
            "medianActiveBlockFraction": med(subset, "activeBlockFraction"),
            "nWrong": len(wrong),
            "medianMotionWrong": med(wrong, "motionMean"),
            "medianMotionRight": med(right, "motionMean"),
            "medianLumaWrong": med(wrong, "lumaMean"),
            "medianLumaRight": med(right, "lumaMean"),
            "irLikeShareWrongPercent": round(sum(1 for s in wrong if s["isInfraredLike"]) / len(wrong) * 100, 1)
            if wrong else None,
            "irLikeShareRightPercent": round(sum(1 for s in right if s["isInfraredLike"]) / len(right) * 100, 1)
            if right else None,
        }
    confident_wrong = [s for s in usable if not s["correct"] and s["confidence"] >= 0.8]
    errors = [s for s in usable if not s["correct"]]
    return {
        "usableClips": len(usable),
        "irLikeThresholdSaturation": IR_SAT_THRESHOLD,
        "irLikeSharePercent": round(sum(1 for s in usable if s["isInfraredLike"]) / len(usable) * 100, 1),
        "medianConfidenceOnErrors": round(statistics.median([s["confidence"] for s in errors]), 4) if errors else None,
        "medianConfidenceOnCorrect": round(
            statistics.median([s["confidence"] for s in usable if s["correct"]]), 4
        ) if usable else None,
        "confidentlyWrongSharePercent": round(len(confident_wrong) / len(errors) * 100, 1) if errors else None,
        "byClass": by_class,
        "byPredictedClass": by_predicted_class(usable),
        "motionTertileErrorRate": motion_tertile_error_rate(usable),
    }


def by_predicted_class(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """按「模型判成什么」分组的运动量：说明模型其实靠画面运动量在分流。"""
    result: dict[str, Any] = {}
    for label in sorted({s["predicted"] for s in stats}):
        subset = [s for s in stats if s["predicted"] == label]
        if not subset:
            continue
        result[label] = {
            "n": len(subset),
            "medianMotion": round(statistics.median([s["motionMean"] for s in subset]), 3),
            "medianLocalMotionP95": round(statistics.median([s["localMotionP95"] for s in subset]), 3),
            "precisionCheck": round(
                sum(1 for s in subset if s["correct"]) / len(subset) * 100, 1
            ),
        }
    return result


def motion_tertile_error_rate(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """类内按运动量三分位看错误率：证实「低运动片段更容易被判成静止/慢动作」。"""
    result: dict[str, Any] = {}
    for label in sorted({s["label"] for s in stats}):
        subset = sorted([s for s in stats if s["label"] == label], key=lambda s: s["motionMean"])
        if len(subset) < 9:
            continue
        size = len(subset) // 3
        buckets = {
            "low": subset[:size],
            "mid": subset[size:2 * size],
            "high": subset[2 * size:],
        }
        result[label] = {
            name: {
                "n": len(items),
                "medianMotion": round(statistics.median([i["motionMean"] for i in items]), 3),
                "errorRatePercent": round(sum(1 for i in items if not i["correct"]) / len(items) * 100, 1),
            }
            for name, items in buckets.items()
        }
    return result


def summarize_interval_spread(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """同一标注区间切出多个窗口时，窗口间运动量差多少。

    一个区间只有一个标签，但区间可能横跨多种行为（例如先走动再长时间站定）。
    这里用「窗口间运动量极差倍数」和「是否同时跨过活动档/静止档」作为漂移的代理指标。
    """
    usable = [c for c in stats if not c.get("missing")]
    groups: dict[str, list[dict[str, Any]]] = {}
    for clip in usable:
        groups.setdefault(clip["sample_id"], []).append(clip)
    multi = {key: items for key, items in groups.items() if len(items) >= 2}
    rows: list[dict[str, Any]] = []
    for key, items in multi.items():
        motions = [item["motionMean"] for item in items]
        low, high = min(motions), max(motions)
        rows.append({
            "sampleId": key,
            "label": items[0]["label"],
            "clips": len(items),
            "minMotion": round(low, 3),
            "maxMotion": round(high, 3),
            "spreadRatio": round(high / low, 2) if low > 0 else None,
            "crossesActivityStationary": bool(high >= 15 and low <= 5),
        })
    total = len(groups)
    ratios = [r["spreadRatio"] for r in rows if r["spreadRatio"]]
    by_label: dict[str, Any] = {}
    for row in rows:
        bucket = by_label.setdefault(row["label"], {"intervals": 0, "crossing": 0})
        bucket["intervals"] += 1
        bucket["crossing"] += 1 if row["crossesActivityStationary"] else 0
    return {
        "intervals": total,
        "multiWindowIntervals": len(rows),
        "singleWindowIntervals": total - len(rows),
        "medianSpreadRatio": round(statistics.median(ratios), 2) if ratios else None,
        "spreadRatioAtLeast3": sum(1 for r in ratios if r >= 3),
        "spreadRatioAtLeast5": sum(1 for r in ratios if r >= 5),
        "spreadRatioAtLeast10": sum(1 for r in ratios if r >= 10),
        "crossingIntervals": sum(1 for r in rows if r["crossesActivityStationary"]),
        "crossingByLabel": by_label,
        "rows": sorted(rows, key=lambda r: -(r["spreadRatio"] or 0)),
    }


def class_cases(data: dict[str, Any], visual: list[dict[str, Any]], label: str,
                want_correct: int, want_wrong: int) -> list[dict[str, Any]]:
    """按类别取若干判对/判错的片段，附带判断依据所需的描述量。

    判错侧取置信度最高的几条（模型最"确信地错"的那些）；判对侧按亮度分位铺开，
    避免只挑到同一类光照条件下的样本。两侧都按源视频去重。
    """
    classes: list[str] = data["classes"]
    if label not in classes:
        raise SystemExit(f"没有类别 {label}")
    index = classes.index(label)
    by_id = {item["sample_id"] + "@" + item["clip"]: item for item in visual if not item.get("missing")}

    def source_of(sample: str) -> str:
        return sample.rsplit(":", 2)[0]

    def build(pred: dict[str, Any]) -> dict[str, Any] | None:
        key = pred["sample_id"] + "@" + Path(pred["video"]).name
        meta = by_id.get(key)
        if meta is None:
            return None
        return {
            "sampleId": pred["sample_id"],
            "clip": Path(pred["video"]).name,
            "source": source_of(pred["sample_id"]),
            "true": classes[pred["label"]],
            "predicted": classes[pred["predicted"]],
            "correct": pred["label"] == pred["predicted"],
            "confidence": round(max(pred["scores"]), 4),
            "motionMean": meta.get("motionMean"),
            "localMotionP95": meta.get("localMotionP95"),
            "lumaMean": meta.get("lumaMean"),
            "isInfraredLike": meta.get("isInfraredLike"),
        }

    rows = [build(p) for p in data["predictions"] if p["label"] == index]
    rows = [r for r in rows if r]
    wrong = sorted([r for r in rows if not r["correct"]], key=lambda r: -r["confidence"])
    correct = sorted([r for r in rows if r["correct"]], key=lambda r: -(r["lumaMean"] or 0))

    def take_by_source(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        """按来源轮转取样：同一来源只出一条，先把来源铺开，再放宽。

        否则判对侧会被单一来源（同一家庭的狗扒门）占满，读者会以为那是全类的典型画面。
        """
        buckets: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            buckets.setdefault(item["source"], []).append(item)
        for bucket in buckets.values():
            bucket.sort(key=lambda item: -(item["lumaMean"] or 0))
        order = sorted(buckets.values(), key=lambda bucket: -len(bucket))
        picked: list[dict[str, Any]] = []
        used_clips: set[str] = set()
        round_index = 0
        while len(picked) < count and any(len(bucket) > round_index for bucket in order):
            for bucket in order:
                if len(picked) >= count:
                    break
                if len(bucket) <= round_index:
                    continue
                item = bucket[round_index]
                if item["clip"] in used_clips:
                    continue
                used_clips.add(item["clip"])
                picked.append(item)
            round_index += 1
        return picked[:count]

    def take_wrong(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        """判错侧：先按置信度取「最确信地错」，再补不同去向的，避免全是同一去向。"""
        picked: list[dict[str, Any]] = []
        used_sources: set[str] = set()
        used_clips: set[str] = set()
        primary = [item for item in items if item["predicted"] == "activity"]
        others = [item for item in items if item["predicted"] != "activity"]
        plan = primary[: max(0, count - 2)] + others[:2]
        for item in plan + items:
            if len(picked) >= count:
                break
            if item["clip"] in used_clips:
                continue
            if item["source"] in used_sources and len(picked) < count - 1:
                continue
            used_sources.add(item["source"])
            used_clips.add(item["clip"])
            picked.append(item)
        return picked[:count]

    chosen = take_wrong(wrong, want_wrong) + take_by_source(correct, want_correct)
    for position, item in enumerate(chosen, start=1):
        verdict = "correct" if item["correct"] else "wrong"
        item["id"] = f"{label}-{verdict}-{position:02d}"
        item["pair"] = f"{label}->{item['predicted']}"
    return chosen


def motion_profile(video: Path, bucket: float) -> dict[str, Any]:
    """逐帧帧差 → 按时间桶汇总，用于看一个区间内部行为是否换过档。"""
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"打不开区间视频：{video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 15.0)
    series: list[dict[str, float]] = []
    previous = None
    index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if previous is not None:
                series.append({"t": round(index / fps, 3), "motion": round(float(np.abs(gray - previous).mean()), 3)})
            previous = gray
            index += 1
    finally:
        capture.release()
    if not series:
        raise SystemExit(f"区间视频没有可用帧：{video}")
    buckets: list[dict[str, Any]] = []
    size = max(1, int(round(bucket * fps)))
    for start in range(0, len(series), size):
        chunk = series[start:start + size]
        buckets.append({
            "from": round(chunk[0]["t"], 2),
            "to": round(chunk[-1]["t"] + 1 / fps, 2),
            "mean": round(float(np.mean([c["motion"] for c in chunk])), 3),
            "max": round(float(np.max([c["motion"] for c in chunk])), 3),
        })
    return {"video": str(video), "fps": round(fps, 3), "frames": index + 1,
            "seconds": round((index + 1) / fps, 2), "bucketSeconds": bucket,
            "perFrame": series, "buckets": buckets}


def pick_cases(data: dict[str, Any], case_flows: dict[str, Any], per_pair: int, min_conf: float) -> list[dict[str, Any]]:
    classes: list[str] = data["classes"]
    preds = data["predictions"]
    candidates: list[dict[str, Any]] = []
    for flow in case_flows["flows"]:
        true_label = flow["label"]
        for dest in flow["destinations"]:
            pairs = [
                p for p in preds
                if classes[p["label"]] == true_label
                and classes[p["predicted"]] == dest["label"]
                and max(p["scores"]) >= min_conf
            ]
            pairs.sort(key=lambda p: -max(p["scores"]))
            used_sources: set[str] = set()
            used_clips: set[str] = set()
            picked = 0
            for pred in pairs:
                source = pred["sample_id"].rsplit(":", 1)[0].rsplit(":", 1)[0]
                clip_name = Path(pred["video"]).name
                if source in used_sources or clip_name in used_clips:
                    continue
                used_sources.add(source)
                used_clips.add(clip_name)
                candidates.append({
                    "pair": f"{true_label}->{dest['label']}",
                    "true": true_label,
                    "predicted": dest["label"],
                    "pairCount": dest["count"],
                    "sample_id": pred["sample_id"],
                    "clip": clip_name,
                    "sourceVideo": source,
                    "confidence": round(max(pred["scores"]), 4),
                    "startFrame": pred["start_frame"],
                    "endFrame": pred["end_frame"],
                })
                picked += 1
                if picked >= per_pair:
                    break
    # 同时给几个判对的样本作对照（每类取置信度最高的一条）。
    for index, name in enumerate(classes):
        correct = [p for p in preds if p["label"] == index and p["predicted"] == index]
        correct.sort(key=lambda p: -max(p["scores"]))
        used_clips: set[str] = set()
        picked = 0
        for pred in correct:
            clip_name = Path(pred["video"]).name
            if clip_name in used_clips:
                continue
            used_clips.add(clip_name)
            candidates.append({
                "pair": f"{name}->{name}",
                "true": name,
                "predicted": name,
                "pairCount": len(correct),
                "sample_id": pred["sample_id"],
                "clip": clip_name,
                "sourceVideo": pred["sample_id"].rsplit(":", 1)[0].rsplit(":", 1)[0],
                "confidence": round(max(pred["scores"]), 4),
                "startFrame": pred["start_frame"],
                "endFrame": pred["end_frame"],
            })
            picked += 1
            if picked >= 2:
                break
    for position, case in enumerate(candidates, start=1):
        case["id"] = f"{case['pair'].replace('->', '-to-')}-{position:03d}"
    return candidates


def contact_sheet(cases: list[dict[str, Any]], clips_dir: Path, out: Path,
                  columns: int, frame_index: int, font_path: str = "") -> dict[str, Any]:
    """每段取一帧拼成一张对照图，图上写清它是判对还是判错、置信度与光照。

    cv2 的 putText 只支持 ASCII，标签用 PIL 画（中文类名与结论要能读）。
    """
    from PIL import Image, ImageDraw, ImageFont  # 延迟导入：只有这个子命令需要

    font_candidates = [
        font_path, "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    font = None
    for candidate in font_candidates:
        if not candidate:
            continue
        try:
            font = ImageFont.truetype(candidate, 15)
            break
        except OSError:
            continue
    if font is None:
        raise SystemExit("找不到中文字体，请用 --font 指定（对照图标签需要中文）")

    tiles: list[Image.Image] = []
    missing = 0
    caption_h = 46
    for case in cases:
        capture = cv2.VideoCapture(str(clips_dir / case["clip"]))
        if not capture.isOpened():
            missing += 1
            capture.release()
            continue
        ok, frame = False, None
        for _ in range(frame_index):
            ok, frame = capture.read()
            if not ok:
                break
        capture.release()
        if not ok or frame is None:
            missing += 1
            continue
        rgb = cv2.cvtColor(cv2.resize(frame, (TILE_SIZE, TILE_SIZE), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2RGB)
        tile = Image.new("RGB", (TILE_SIZE, TILE_SIZE + caption_h), (18, 18, 20))
        tile.paste(Image.fromarray(rgb), (0, 0))
        draw = ImageDraw.Draw(tile)
        number = case["id"].rsplit("-", 1)[-1]
        verdict = "判对" if case["correct"] else "判错"
        draw.text((6, TILE_SIZE + 3),
                  f"#{number} {verdict} → {case['predicted']}  {case['confidence']:.2f}",
                  font=font, fill=(255, 255, 255))
        detail = f"亮度 {case.get('lumaMean', 0):.0f}{'（红外）' if case.get('isInfraredLike') else ''}  运动 {case.get('motionMean', 0):.1f}"
        draw.text((6, TILE_SIZE + 23), detail, font=font, fill=(168, 186, 206))
        tiles.append(tile)

    if not tiles:
        raise SystemExit("没有可用的片段帧，无法生成对照图")
    rows = math.ceil(len(tiles) / columns)
    tile_w, tile_h = tiles[0].size
    sheet = Image.new("RGB", (columns * tile_w + 8, rows * tile_h + 8), (24, 24, 26))
    for position, tile in enumerate(tiles):
        row, col = divmod(position, columns)
        sheet.paste(tile, (col * tile_w + 4, row * tile_h + 4))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    return {"tiles": len(tiles), "missing": missing, "out": str(out)}


def render_strip(clip: Path, out: Path, frames_to_take: int = 6) -> None:
    cap = cv2.VideoCapture(str(clip))
    if not cap.isOpened():
        raise SystemExit(f"打不开片段：{clip}")
    images: list[np.ndarray] = []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 60
    wanted = {int(round(i * (total - 1) / (frames_to_take - 1))) for i in range(frames_to_take)}
    index = 0
    while images.__len__() < frames_to_take:
        ok, frame = cap.read()
        if not ok:
            break
        if index in wanted:
            label = f"{index / 15.0:04.1f}s"
            canvas = frame.copy()
            cv2.rectangle(canvas, (4, 4), (62, 20), (0, 0, 0), -1)
            cv2.putText(canvas, label, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
            images.append(canvas)
        index += 1
    cap.release()
    if not images:
        raise SystemExit(f"片段没有可读帧：{clip}")
    height, width = images[0].shape[:2]
    cols = 3
    rows = math.ceil(len(images) / cols)
    sheet = np.full((rows * height, cols * width, 3), 24, dtype=np.uint8)
    for position, image in enumerate(images):
        row, col = divmod(position, cols)
        sheet[row * height:(row + 1) * height, col * width:(col + 1) * width] = image
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])


def render_video(clip: Path, out: Path, fps: float) -> None:
    cap = cv2.VideoCapture(str(clip))
    if not cap.isOpened():
        raise SystemExit(f"打不开片段：{clip}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = H264VideoWriter(str(out), fps=fps, size=(width, height), crf=21)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
    finally:
        writer.release()
        cap.release()


def main() -> None:
    args = parse_args()
    if args.command == "stats":
        data = load_metrics(args.metrics)
        args.out.mkdir(parents=True, exist_ok=True)
        rows = per_class_table(data)
        flows = error_flows(data)
        visual = clip_visual_stats(data, args.clips_dir)
        visual_summary = summarise_visual(visual)
        (args.out / "per_class.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        (args.out / "error_flows.json").write_text(json.dumps(flows, ensure_ascii=False, indent=2))
        (args.out / "clip_visual_stats.json").write_text(json.dumps(visual, ensure_ascii=False, indent=2))
        spread = summarize_interval_spread(visual)
        (args.out / "interval_spread.json").write_text(json.dumps(spread, ensure_ascii=False, indent=2))
        breakdown = source_breakdown(data)
        (args.out / "source_breakdown.json").write_text(json.dumps(breakdown, ensure_ascii=False, indent=2))
        summary = {
            "sourceMetrics": str(args.metrics),
            "classes": data["classes"],
            "samples": data.get("samples"),
            "distinctIntervals": len({p["sample_id"] for p in data["predictions"]}),
            "top1Percent": round(data.get("top1_acc_percent", 0.0), 2),
            "macroF1Percent": round(data.get("macro_f1_percent", 0.0), 2),
            "balancedAccPercent": round(data.get("balanced_acc_percent", 0.0), 2),
            "macroRecallPercent": round(
                statistics.mean([r["recallPercent"] for r in rows if r["support"]]), 2
            ),
            "macroRecallExcludingZeroSupport": round(
                statistics.mean([r["recallPercent"] for r in rows if r["support"] and r["support"] >= 10]), 2
            ),
            "activitySink": flows["activitySink"],
            "intervalSpread": {k: v for k, v in spread.items() if k not in ("rows", "crossingByLabel")},
            "sources": breakdown["sources"],
            "visualSummary": visual_summary,
        }
        (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(json.dumps({
            "out": str(args.out),
            "top1": summary["top1Percent"],
            "macroRecall": summary["macroRecallPercent"],
            "sink": summary["activitySink"],
        }, ensure_ascii=False, indent=2))
    elif args.command == "class-cases":
        data = load_metrics(args.metrics)
        visual = load_json(args.analysis / "clip_visual_stats.json", "逐片段描述量")
        chosen = class_cases(data, visual, args.label, args.correct, args.wrong)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(chosen, ensure_ascii=False, indent=2))
        print(f"写入 {args.out}：{len(chosen)} 条（判错 {sum(1 for c in chosen if not c['correct'])}，"
              f"判对 {sum(1 for c in chosen if c['correct'])}）")
    elif args.command == "profile":
        profile = motion_profile(args.video, args.bucket)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
        print(json.dumps({"out": str(args.out), "seconds": profile["seconds"],
                          "buckets": len(profile["buckets"])}, ensure_ascii=False))
    elif args.command == "cases":
        data = load_metrics(args.metrics)
        flows = error_flows(data)
        cases = pick_cases(data, flows, args.per_pair, args.min_conf)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(cases, ensure_ascii=False, indent=2))
        pairs = sorted({c["pair"] for c in cases})
        print(f"写入 {args.out}：{len(cases)} 个候选，覆盖 {len(pairs)} 个混淆对")
    elif args.command == "sheet":
        cases = load_json(args.cases, "案例清单")
        result = contact_sheet(cases, args.clips_dir, args.out, args.columns, args.frame, args.font)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "media":
        cases = load_json(args.cases or (args.analysis / "cases.json"), "案例清单")
        selected = {token.strip() for token in args.select.split(",") if token.strip()}
        if selected:
            cases = [c for c in cases if c["id"] in selected]
        if not cases:
            raise SystemExit("没有匹配的 case id")
        rendered = []
        for case in cases:
            clip = args.clips_dir / case["clip"]
            if not clip.exists():
                print(f"[warn] 缺片段：{clip}", file=sys.stderr)
                continue
            # 短片用于展示动作过程，条纹图用于在没有播放器的场合也能看到关键帧。
            video = args.media_out / f"{case['id']}.mp4"
            image = args.assets_out / f"{case['id']}.jpg"
            render_video(clip, video, args.fps)
            render_strip(clip, image)
            rendered.append({**case, "image": str(image), "video": str(video)})
        (args.analysis / "rendered_cases.json").write_text(json.dumps(rendered, ensure_ascii=False, indent=2))
        print(f"渲染 {len(rendered)} 个案例 → {args.assets_out} / {args.media_out}")


if __name__ == "__main__":
    main()
