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

    p_media = sub.add_parser("media", help="render selected cases to strips / mp4")
    p_media.add_argument("--analysis", type=Path, required=True)
    p_media.add_argument("--clips-dir", type=Path, required=True)
    p_media.add_argument("--assets-out", type=Path, required=True)
    p_media.add_argument("--media-out", type=Path, required=True)
    p_media.add_argument("--select", type=str, default="", help="逗号分隔的 case id，默认渲染全部")
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


def load_metrics(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    for key in ("classes", "per_class", "confusion_matrix", "predictions"):
        if key not in data:
            raise SystemExit(f"{path} 缺少字段 {key}，不是预期的 test_metrics.json")
    return data


def per_class_table(data: dict[str, Any]) -> list[dict[str, Any]]:
    classes: list[str] = data["classes"]
    preds = data["predictions"]
    matrix = data["confusion_matrix"]
    total = len(preds)
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
        breakdown = source_breakdown(data)
        (args.out / "source_breakdown.json").write_text(json.dumps(breakdown, ensure_ascii=False, indent=2))
        summary = {
            "sourceMetrics": str(args.metrics),
            "classes": data["classes"],
            "samples": data.get("samples"),
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
    elif args.command == "cases":
        data = load_metrics(args.metrics)
        flows = error_flows(data)
        cases = pick_cases(data, flows, args.per_pair, args.min_conf)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(cases, ensure_ascii=False, indent=2))
        pairs = sorted({c["pair"] for c in cases})
        print(f"写入 {args.out}：{len(cases)} 个候选，覆盖 {len(pairs)} 个混淆对")
    elif args.command == "media":
        cases = json.loads((args.analysis / "cases.json").read_text())
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
