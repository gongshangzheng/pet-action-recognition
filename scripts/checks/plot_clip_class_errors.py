#!/usr/bin/env python3
"""把 `analyze_clip_class_errors.py` 的输出画成报告用的 PNG 图。

四张图对应报告里的四件事，不追求覆盖所有指标：

1. `fig-class-overview.png`——类别分布与逐类召回（带 95% Wilson 区间）；
2. `fig-confusion.png`——混淆矩阵热图；
3. `fig-motion-surface.png`——模型按「画面运动量」分流的证据（预测类别 vs 真实类别的运动量区间）；
4. `fig-error-by-motion.png`——类内按运动量三分位的错误率。

用法：

    python3 scripts/checks/plot_clip_class_errors.py \
        --analysis results/cat_clip_v9_analysis/analysis \
        --out results/cat_clip_v9_analysis/figures
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

CJK_FONT_CANDIDATES = (
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)

INK = (38, 42, 48)
MUTED = (120, 128, 136)
GRID = (226, 230, 234)
BAR = (96, 125, 158)
HIGHLIGHT = (200, 92, 60)
ACCENT = (34, 130, 118)
SOFT = (232, 236, 240)
BACKGROUND = (255, 255, 255)
# 报告里做区间对照的那条样本（正文第一节）
INTERVAL_SAMPLE_ID = "event_20260802_053844:1-235:activity"
# 端到端诊断量 = 可用率 85.03% × 条件准确率 85.75%（AGENTS.md 口径，片段级只能估计）。
# 放在图里的目的是把「条件准确率」和「端到端」两个数并排，避免把 85.75% 读成端到端成绩。
END_TO_END_ESTIMATE_PERCENT = 72.9


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font", default="", help="CJK 字体路径，默认按候选列表探测")
    return parser.parse_args()


def load_font(size: int, explicit: str = "") -> ImageFont.FreeTypeFont:
    candidates: Iterable[str] = (explicit,) if explicit else CJK_FONT_CANDIDATES
    for path in candidates:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise SystemExit("找不到可用的中文字体，请用 --font 指定（脚本无法用默认位图字体画中文）")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), BACKGROUND)
    return image, ImageDraw.Draw(image)


def draw_title(draw: ImageDraw.ImageDraw, text: str, subtitle: str, font_title, font_body) -> None:
    draw.text((48, 34), text, font=font_title, fill=INK)
    if subtitle:
        draw.text((48, 76), subtitle, font=font_body, fill=MUTED)


def shorten(label: str, limit: int = 20) -> str:
    return label if len(label) <= limit else label[: limit - 1] + "…"


# 列宽有限，坐标轴标题用短名；行标题保留全名，全文以行标题为准。
SHORT_NAMES = {
    "prolonged_stationary": "prolonged",
    "gnawing": "gnawing",
}


def short_name(label: str) -> str:
    return SHORT_NAMES.get(label, shorten(label, 12))


def wrap_label(label: str) -> list[str]:
    """把长类名按 `_` 折成两行，避免横轴标签互相压字。"""
    if len(label) <= 12:
        return [label]
    head, _, tail = label.partition("_")
    return [head, tail] if tail else [label]


def figure_class_overview(rows: list[dict[str, Any]], summary: dict[str, Any],
                          out: Path, explicit_font: str) -> None:
    """同一张图里放两个口径：整体准确率（达标判定用）与逐类准确率（类内召回）。"""
    title_font = load_font(30, explicit_font)
    label_font = load_font(19, explicit_font)
    body_font = load_font(17, explicit_font)
    small_font = load_font(15, explicit_font)

    ordered = sorted([r for r in rows if r["support"] > 0], key=lambda r: -r["support"])
    sink = summary.get("activitySink", {})
    overall = [
        ("条件 top-1 准确率", summary["top1Percent"], "达标判定用这个数"),
        ("端到端准确率（估计）", END_TO_END_ESTIMATE_PERCENT, "可用率 × 条件准确率"),
        ("macro-F1", summary["macroF1Percent"], "十类等权，不可评估类计 0"),
        ("balanced accuracy", summary["balancedAccPercent"], "十类等权召回"),
        ("对照：永远判 activity", sink.get("alwaysActivityBaselinePercent", 0.0), "单类捷径基线"),
    ]

    axis_x0, axis_w = 500, 660
    width = 1400
    top_rows, class_row_h, overall_row_h = len(overall), 50, 40
    class_top = 184 + overall_row_h * top_rows + 92
    height = class_top + class_row_h * len(ordered) + 110
    image, draw = canvas(width, height)

    def axis_x(value: float) -> float:
        return axis_x0 + axis_w * max(0.0, min(100.0, value)) / 100

    draw_title(
        draw,
        "两个口径要分开看：整体准确率 vs 逐类准确率",
        "上：整体口径，竖线 75% 是项目的闭集准确率目标（达标判定用条件 top-1，测试集口径）",
        title_font,
        body_font,
    )
    draw.text((48, 104), "下：逐类准确率（该类样本被判对的比例，等价于该类召回率）；它的补数就是该类漏检率。"
                         "逐类没有独立的验收线，只作诊断。", font=body_font, fill=MUTED)

    # ---- 整体口径 ----
    draw.text((48, 150), "整体口径（同一批 1,130 条片段）", font=label_font, fill=INK)
    overall_top = 184
    for tick in (0, 25, 50, 75, 100):
        x = axis_x(tick)
        draw.line([(x, overall_top - 8), (x, overall_top + overall_row_h * top_rows - 10)], fill=GRID, width=1)
        draw.text((x - 10, overall_top + overall_row_h * top_rows - 4), str(tick), font=small_font, fill=MUTED)
    target_x = axis_x(75)
    draw.line([(target_x, overall_top - 14), (target_x, overall_top + overall_row_h * top_rows - 10)],
              fill=(214, 168, 96), width=2)
    draw.text((target_x + 6, overall_top - 32), "75% 目标", font=small_font, fill=(176, 128, 56))

    for index, (name, value, hint) in enumerate(overall):
        y = overall_top + index * overall_row_h
        draw.text((48, y + 4), name, font=small_font if len(name) > 12 else label_font, fill=INK)
        color = ACCENT if value >= 75 else (HIGHLIGHT if value < 70 else (198, 150, 86))
        draw.rectangle([axis_x0, y + 8, axis_x(value), y + 26], fill=color)
        draw.text((axis_x(value) + 10, y + 4), f"{value:.2f}", font=small_font, fill=INK)
        draw.text((axis_x(value) + 68, y + 6), hint, font=small_font, fill=MUTED)

    # ---- 逐类口径 ----
    draw.text((48, class_top - 56), "逐类准确率（实心）与 precision（空心），按支持度排序", font=label_font, fill=INK)
    draw.text((250, class_top - 28), "支持度", font=small_font, fill=MUTED)
    draw.text((axis_x0, class_top - 28), "准确率 / precision %", font=small_font, fill=MUTED)

    for tick in (0, 25, 50, 75, 100):
        x = axis_x(tick)
        draw.line([(x, class_top - 8), (x, class_top + class_row_h * len(ordered) - 10)], fill=GRID, width=1)
        draw.text((x - 10, class_top + class_row_h * len(ordered) - 4), str(tick), font=small_font, fill=MUTED)
    draw.line([(target_x, class_top - 10), (target_x, class_top + class_row_h * len(ordered) - 10)],
              fill=(214, 168, 96), width=1)
    draw.text((target_x + 6, class_top + class_row_h * len(ordered) - 22), "75% 参照", font=small_font,
              fill=(176, 128, 56))

    max_support = max(r["support"] for r in ordered)
    for index, row in enumerate(ordered):
        y = class_top + index * class_row_h
        draw.text((48, y + 6), row["label"], font=small_font if len(row["label"]) > 18 else label_font, fill=INK)
        support_w = 110 * row["support"] / max_support
        draw.rectangle([250, y + 10, 250 + max(2, support_w), y + 30], fill=SOFT)
        draw.text((370, y + 6), f"{row['support']} ({row['supportSharePercent']:.1f}%)",
                  font=small_font, fill=MUTED)

        recall = row["recallPercent"]
        color = HIGHLIGHT if recall < 70 else (198, 150, 86) if recall < 80 else BAR
        draw.rectangle([axis_x0, y + 10, axis_x(recall), y + 30], fill=color)
        low, high = row["recallCi95"]
        draw.line([(axis_x(low), y + 20), (axis_x(high), y + 20)], fill=INK, width=2)
        draw.line([(axis_x(low), y + 14), (axis_x(low), y + 26)], fill=INK, width=2)
        draw.line([(axis_x(high), y + 14), (axis_x(high), y + 26)], fill=INK, width=2)
        # precision：空心方块标在同一刻度上，避免只看到召回而误判「报得准不准」
        px = axis_x(row["precisionPercent"])
        draw.rectangle([px - 6, y + 14, px + 6, y + 26], outline=ACCENT, width=2)
        draw.text((axis_x0 + axis_w + 12, y + 6),
                  f"{recall:.1f} / {row['precisionPercent']:.1f}", font=small_font, fill=INK)

    note = ("注：gnawing（4 条）、fall / seizure（0 条）样本不足，区间宽度本身说明它们不能作为结论；"
            "端到端与 macro/balanced 两类口径的分母不同，不能与 top-1 直接比较。")
    draw.text((48, height - 52), note, font=small_font, fill=MUTED)
    image.save(out)


def figure_interval_evidence(analysis: Path, sample_id: str, out: Path, explicit_font: str) -> None:
    """左：一个区间内部的运动量曲线与三个片段的落点；右：313 个多窗口区间的漂移分布。"""
    title_font = load_font(30, explicit_font)
    body_font = load_font(17, explicit_font)
    label_font = load_font(18, explicit_font)
    small_font = load_font(15, explicit_font)

    profile = json.loads((analysis / "interval_profile.json").read_text())
    spread = json.loads((analysis / "interval_spread.json").read_text())
    clips = json.loads((analysis / "clip_visual_stats.json").read_text())
    cls_label = "prolonged_stationary"
    windows = [c for c in clips if c.get("sample_id") == sample_id and not c.get("missing")]

    def window_span(clip: dict[str, Any]) -> tuple[int, int, str, float]:
        """从片段文件名 `...__<start>-<end>__t0.mp4` 取窗口帧号。"""
        name = clip.get("clip", "")
        token = [part for part in name.split("__") if "-" in part and part.split("-")[-1].isdigit()]
        if not token:
            return 0, 0, clip.get("predicted", ""), clip.get("confidence", 0.0)
        start_frame, end_frame = token[0].split("-")[:2]
        return int(start_frame), int(end_frame), clip.get("predicted", ""), clip.get("confidence", 0.0)

    windows = sorted(windows, key=lambda c: window_span(c)[0])
    width, height = 1400, 840
    image, draw = canvas(width, height)
    draw_title(
        draw,
        "一个 15.7 秒的区间里，行为换过两次档",
        "左：区间内逐帧运动量（0.5 秒一桶）与三个片段的落点；右：313 个多窗口区间的窗口间运动量极差",
        title_font,
        body_font,
    )

    # ---- 左：区间运动量曲线 ----
    x0, y0, plot_w, plot_h = 110, 520, 700, 320
    max_motion = max(8.0, max(b["mean"] for b in profile["buckets"]) * 1.25)
    seconds = profile["seconds"]
    fps = 15.0

    def sx(t: float) -> float:
        return x0 + plot_w * t / seconds

    def sy(value: float) -> float:
        return y0 - plot_h * min(1.0, value / max_motion)

    draw.text((x0, 132), "区间 event_20260802_053844（标注 activity，帧 1–235）", font=label_font, fill=INK)
    # 两段：走动段与站定段（切点取曲线从 >4 落到 <3 的位置，读图即可核对）
    draw.rectangle([sx(0), sy(max_motion), sx(4.3), y0], fill=(238, 243, 248))
    draw.rectangle([sx(4.3), sy(max_motion), sx(14.5), y0], fill=(252, 245, 238))
    draw.text((sx(0.2), sy(max_motion) + 10), "走动 → activity", font=small_font, fill=(60, 96, 140))
    draw.text((sx(5.0), sy(max_motion) + 10), "站定约 10 秒 → 应是 prolonged_stationary", font=small_font, fill=(150, 96, 48))
    draw.text((sx(14.55), sy(max_motion) + 10), "再起步", font=small_font, fill=(60, 96, 140))

    for tick in range(0, int(seconds) + 1, 3):
        draw.line([(sx(tick), y0), (sx(tick), y0 + 5)], fill=MUTED, width=1)
        draw.text((sx(tick) - 10, y0 + 10), f"{tick}s", font=small_font, fill=MUTED)
    draw.line([(x0, y0), (x0 + plot_w, y0)], fill=MUTED, width=1)
    for tick in (0, 2, 4, 6, 8):
        if tick > max_motion:
            continue
        draw.line([(x0 - 6, sy(tick)), (x0, sy(tick))], fill=MUTED, width=1)
        draw.text((x0 - 34, sy(tick) - 9), f"{tick}", font=small_font, fill=MUTED)
    draw.text((x0 - 74, sy(max_motion) - 6), "运动量", font=small_font, fill=MUTED)

    points = [(sx(b["from"] + 0.25), sy(b["mean"])) for b in profile["buckets"]]
    for left, right in zip(points, points[1:], strict=False):
        draw.line([left, right], fill=BAR, width=3)
    for point in points:
        draw.ellipse([point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3], fill=BAR)

    # 三个片段窗口：画成括号，颜色区分是否判错
    for index, clip in enumerate(windows):
        start_frame, end_frame, predicted, confidence = window_span(clip)
        top = y0 + 34 + index * 22
        left_s = sx((start_frame - 1) / fps)
        right_s = sx((end_frame - 1) / fps)
        color = HIGHLIGHT if predicted != cls_label else ACCENT
        draw.line([(left_s, top), (right_s, top)], fill=color, width=6)
        draw.line([(left_s, top - 5), (left_s, top + 5)], fill=color, width=2)
        draw.line([(right_s, top - 5), (right_s, top + 5)], fill=color, width=2)
        draw.text((right_s + 8, top - 8), f"{start_frame}–{end_frame}", font=small_font, fill=color)

    detail = " / ".join(
        f"{window_span(c)[0]}–{window_span(c)[1]} 帧 → {c.get('predicted')}（{c.get('confidence', 0):.2f}）"
        for c in windows
    )
    draw.text((x0, y0 + 34 + len(windows) * 22 + 14),
              "三个窗口全部落在站定段：" + detail, font=body_font, fill=INK)
    draw.text((x0, y0 + 34 + len(windows) * 22 + 40),
              "同一个区间贡献了 3 条「错判」，其实是区间内标签漂移。", font=body_font, fill=INK)

    # ---- 右：极差分布 ----
    rx, ry, rw, rh = 900, 520, 420, 320
    ratios = sorted(r["spreadRatio"] for r in spread["rows"] if r.get("spreadRatio"))
    cap = 12.0
    bins = 24
    counts = [0] * bins
    for value in ratios:
        counts[min(bins - 1, int(value / cap * bins))] += 1
    peak = max(counts) or 1
    draw.text((rx, 132), "窗口间运动量极差（313 个多窗口区间）", font=label_font, fill=INK)
    for index, count in enumerate(counts):
        bar_h = rh * count / peak
        left = rx + rw * index / bins
        draw.rectangle([left + 1, ry - bar_h, left + rw / bins - 2, ry], fill=BAR)
    draw.line([(rx, ry), (rx + rw, ry)], fill=MUTED, width=1)
    for tick in (0, 3, 6, 9, 12):
        x = rx + rw * min(1.0, tick / cap)
        draw.line([(x, ry), (x, ry + 5)], fill=MUTED, width=1)
        draw.text((x - 12, ry + 10), f"{tick}×", font=small_font, fill=MUTED)
    for value, label in ((3, "≥3×：69 个"), (5, "≥5×：29 个")):
        x = rx + rw * value / cap
        draw.line([(x, ry - rh), (x, ry)], fill=(214, 168, 96), width=2)
        draw.text((x + 4, ry - rh + 2), label, font=small_font, fill=(150, 104, 40))

    summary_lines = [
        f"中位极差 {spread['medianSpreadRatio']}×，最大 {ratios[-1]:.1f}×；示例区间 6.1×",
        f"{spread['crossingIntervals']}/{spread['multiWindowIntervals']} 个区间同时出现「活动档」与「静止档」窗口",
        "极差越大，越可能是一个标签盖住了多段行为；",
        "窗口只覆盖区间的一部分，所以这是漂移规模的下限。",
    ]
    for index, line in enumerate(summary_lines):
        draw.text((rx - 60, ry + 46 + index * 24), line, font=small_font, fill=INK if index < 2 else MUTED)

    image.save(out)


def figure_confusion(matrix: list[list[int]], classes: list[str], out: Path, explicit_font: str) -> None:
    rows = [index for index, name in enumerate(classes) if sum(matrix[index]) > 0]
    cols = [index for index, name in enumerate(classes) if any(matrix[r][index] for r in range(len(classes)))]
    title_font = load_font(30, explicit_font)
    body_font = load_font(18, explicit_font)
    label_font = load_font(17, explicit_font)
    cell_font = load_font(19, explicit_font)

    cell = 124
    left, top = 270, 184
    width = left + cell * len(cols) + 60
    height = top + cell * len(rows) + 110
    image, draw = canvas(width, height)
    draw_title(
        draw,
        "混淆矩阵：行为真实类别，列为模型预测",
        "数值为片段条数；对角线为判对。空格为 0，未列入 fall / seizure（测试集无样本）",
        title_font,
        body_font,
    )

    for col, pred_index in enumerate(cols):
        draw.text((left + col * cell + 6, top - 30), short_name(classes[pred_index]), font=label_font, fill=MUTED)
    max_off = max(matrix[r][c] for r in rows for c in cols if r != c)

    for row_position, true_index in enumerate(rows):
        y = top + row_position * cell
        draw.text((48, y + cell // 2 - 10), classes[true_index], font=label_font, fill=INK)
        for col_position, pred_index in enumerate(cols):
            x = left + col_position * cell
            count = matrix[true_index][pred_index]
            if count == 0:
                fill = (248, 249, 250)
            elif true_index == pred_index:
                fill = (206, 230, 224)
            else:
                weight = count / max_off
                fill = (255, int(238 - 78 * weight), int(232 - 108 * weight))
            draw.rectangle([x, y, x + cell - 6, y + cell - 6], fill=fill)
            if count:
                text_color = INK if true_index == pred_index else (110, 44, 26)
                draw.text((x + 14, y + cell // 2 - 12), str(count), font=cell_font, fill=text_color)

    draw.text((48, height - 52), "读法：看某一行 → 该类样本被判成了什么；看某一列 → 哪些类被吸进这个预测。",
              font=body_font, fill=MUTED)
    image.save(out)


def figure_motion_surface(clips: list[dict[str, Any]], out: Path, explicit_font: str) -> None:
    title_font = load_font(30, explicit_font)
    body_font = load_font(18, explicit_font)
    label_font = load_font(18, explicit_font)
    small_font = load_font(16, explicit_font)

    usable = [c for c in clips if not c.get("missing")]
    by_true: dict[str, list[float]] = {}
    by_pred: dict[str, list[float]] = {}
    for clip in usable:
        by_true.setdefault(clip["label"], []).append(clip["motionMean"])
        by_pred.setdefault(clip["predicted"], []).append(clip["motionMean"])

    def stats(groups: dict[str, list[float]]) -> list[tuple[str, float, float, float, int]]:
        result = []
        for name, values in groups.items():
            result.append((name, percentile(values, 0.1), percentile(values, 0.9),
                           statistics.median(values), len(values)))
        return sorted(result, key=lambda item: item[3])

    true_rows = stats(by_true)
    pred_rows = stats(by_pred)
    width, height = 1360, 880
    image, draw = canvas(width, height)
    draw_title(
        draw,
        "模型的分流依据几乎是画面运动量",
        "横轴为片段内平均帧差（越大越动），条带为 10–90 百分位区间，竖线为中位数",
        title_font,
        body_font,
    )

    x0, x1 = 300, 1180
    max_motion = max(row[2] for row in true_rows + pred_rows) * 1.05
    panels = (("按真实类别", true_rows, 190), ("按模型预测", pred_rows, 470))
    for panel_name, rows, top in panels:
        draw.text((48, top - 34), panel_name, font=label_font, fill=INK)
        for index, (name, low, high, median, count) in enumerate(rows):
            y = top + index * 30
            draw.text((48, y - 8), f"{shorten(name, 22)} ({count})", font=small_font, fill=MUTED)
            left = x0 + (x1 - x0) * low / max_motion
            right = x0 + (x1 - x0) * high / max_motion
            mid = x0 + (x1 - x0) * median / max_motion
            draw.line([(left, y + 4), (right, y + 4)], fill=BAR, width=7)
            draw.line([(mid, y - 5), (mid, y + 13)], fill=INK, width=3)

    # 两个面板共用一条横轴：网格贯穿到底，刻度只标一次。
    axis_bottom = 470 + 30 * len(pred_rows) + 4
    for tick in (0, 10, 20, 30, 40):
        if tick > max_motion:
            continue
        x = x0 + (x1 - x0) * tick / max_motion
        draw.line([(x, 182), (x, axis_bottom)], fill=GRID, width=1)
        draw.text((x - 8, axis_bottom + 8), str(tick), font=small_font, fill=MUTED)
    draw.text((x1 - 40, axis_bottom + 8), "运动量", font=small_font, fill=MUTED)

    draw.text((48, height - 96), "两组区间大量重叠：同一个运动量档位里同时装着静止、进食、饮水、理毛和活动的片段，",
              font=body_font, fill=INK)
    draw.text((48, height - 68), "所以模型只能在重叠处做取舍，类间边界就落在「动作幅度」而不是「动作语义」上。",
              font=body_font, fill=INK)
    image.save(out)


def figure_error_by_motion(summary: dict[str, Any], out: Path, explicit_font: str) -> None:
    title_font = load_font(30, explicit_font)
    body_font = load_font(18, explicit_font)
    label_font = load_font(18, explicit_font)
    small_font = load_font(15, explicit_font)

    tertiles = summary["visualSummary"]["motionTertileErrorRate"]
    names = sorted(tertiles, key=lambda k: tertiles[k]["mid"]["medianMotion"])
    width, height = 1360, 760
    image, draw = canvas(width, height)
    draw_title(
        draw,
        "类内按运动量三分位的错误率",
        "每类按片段运动量分成低 / 中 / 高三档，柱高为该档被判错的比例——看出哪类是被「运动量阈值」切错的",
        title_font,
        body_font,
    )

    x0, baseline = 150, height - 170
    plot_w, plot_h = 1130, 400
    for tick in (0, 25, 50, 75, 100):
        y = baseline - plot_h * tick / 100
        draw.line([(x0, y), (x0 + plot_w, y)], fill=GRID, width=1)
        draw.text((x0 - 52, y - 9), f"{tick}%", font=small_font, fill=MUTED)

    group_w = plot_w / len(names)
    bar_w = group_w / 4.6
    colors = {"low": (176, 196, 214), "mid": (120, 152, 182), "high": (58, 92, 126)}
    for index, name in enumerate(names):
        lines = wrap_label(name)
        for line_index, line in enumerate(lines):
            draw.text((x0 + index * group_w + 4, baseline + 14 + line_index * 22), line,
                      font=label_font, fill=INK)
        draw.text((x0 + index * group_w + 4, baseline + 14 + len(lines) * 22),
                  f"n={sum(tertiles[name][k]['n'] for k in ('low', 'mid', 'high'))}", font=small_font, fill=MUTED)
        for offset, key in enumerate(("low", "mid", "high")):
            value = tertiles[name][key]["errorRatePercent"]
            bar_h = plot_h * value / 100
            left = x0 + index * group_w + offset * bar_w + 6
            draw.rectangle([left, baseline - bar_h, left + bar_w - 8, baseline], fill=colors[key])
            draw.text((left, baseline - bar_h - 18), f"{value:.0f}", font=small_font, fill=INK)

    legend_x = x0
    for color, label in ((colors["low"], "低运动档"),
                         (colors["mid"], "中运动档"),
                         (colors["high"], "高运动档")):
        draw.rectangle([legend_x, 148, legend_x + 24, 164], fill=color)
        draw.text((legend_x + 32, 144), label, font=small_font, fill=MUTED)
        legend_x += 140
    notes = (
        "scratching 三档齐平（46 / 38 / 46%），说明它的错误不是被运动量阈值切错，而是模式本身与活动重叠；",
        "activity 低运动档 19.6%、高运动档 4.1%，说明活动类的错主要集中在「几乎不动」的片段上。",
    )
    for line_index, line in enumerate(notes):
        draw.text((x0, height - 52 + line_index * 24), line, font=body_font, fill=INK)
    image.save(out)


def main() -> None:
    args = parse_args()
    rows = json.loads((args.analysis / "per_class.json").read_text())
    clips = json.loads((args.analysis / "clip_visual_stats.json").read_text())
    summary = json.loads((args.analysis / "summary.json").read_text())
    # summary 里记了原始指标文件路径（仓库相对路径），混淆矩阵从那里读，不额外复制一份。
    metrics_path = Path(summary.get("sourceMetrics", ""))
    metrics = json.loads(metrics_path.read_text()) if metrics_path.is_file() else None
    classes: list[str] = summary["classes"]
    matrix = metrics["confusion_matrix"] if metrics else summary.get("confusionMatrix")

    args.out.mkdir(parents=True, exist_ok=True)
    figure_class_overview(rows, summary, args.out / "fig-class-overview.png", args.font)
    if matrix:
        figure_confusion(matrix, classes, args.out / "fig-confusion.png", args.font)
    figure_motion_surface(clips, args.out / "fig-motion-surface.png", args.font)
    figure_error_by_motion(summary, args.out / "fig-error-by-motion.png", args.font)
    if (args.analysis / "interval_profile.json").is_file():
        figure_interval_evidence(args.analysis, INTERVAL_SAMPLE_ID, args.out / "fig-interval-drift.png", args.font)
    print(f"图输出到 {args.out}（混淆矩阵：{'用 confusion_matrix' if matrix else '缺失，未画'}）")


if __name__ == "__main__":
    main()
