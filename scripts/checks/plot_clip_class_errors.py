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


def figure_class_overview(rows: list[dict[str, Any]], out: Path, explicit_font: str) -> None:
    title_font = load_font(30, explicit_font)
    label_font = load_font(20, explicit_font)
    body_font = load_font(18, explicit_font)
    small_font = load_font(16, explicit_font)

    ordered = sorted([r for r in rows if r["support"] > 0], key=lambda r: -r["support"])
    width, height = 1360, 200 + len(ordered) * 52
    image, draw = canvas(width, height)
    draw_title(
        draw,
        "类别分布与逐类召回（测试集 1,130 条片段）",
        "左：每类样本数占测试集比例；右：该类被判对的比例，竖线为 95% Wilson 区间",
        title_font,
        body_font,
    )

    left_x, left_w = 250, 280
    right_x, right_w = 760, 480
    top = 150
    row_h = 52
    max_support = max(r["support"] for r in ordered)

    draw.text((left_x, top - 34), "样本数（括号内为占比）", font=small_font, fill=MUTED)
    draw.text((right_x, top - 34), "召回率 %", font=small_font, fill=MUTED)

    for tick in (0, 25, 50, 75, 100):
        x = right_x + right_w * tick / 100
        draw.line([(x, top - 6), (x, top + row_h * len(ordered) - 12)], fill=GRID, width=1)
        draw.text((x - 10, top + row_h * len(ordered) - 4), f"{tick}", font=small_font, fill=MUTED)
    # 75% 是项目的闭集准确率目标，作为参考线而不是验收线（本图是片段级）。
    target_x = right_x + right_w * 0.75
    draw.line([(target_x, top - 10), (target_x, top + row_h * len(ordered) - 12)], fill=(214, 168, 96), width=2)
    draw.text((target_x + 6, top - 30), "75% 目标", font=small_font, fill=(176, 128, 56))

    for index, row in enumerate(ordered):
        y = top + index * row_h
        draw.text((48, y + 8), row["label"], font=small_font if len(row["label"]) > 18 else label_font, fill=INK)
        bar_w = left_w * row["support"] / max_support
        low = row["recallCi95"][0]
        high = row["recallCi95"][1]
        bar_x0 = right_x + right_w * low / 100
        bar_x1 = right_x + right_w * high / 100
        color = HIGHLIGHT if row["recallPercent"] < 80 else BAR
        draw.rectangle([left_x, y + 8, left_x + max(2, bar_w), y + 32], fill=SOFT)
        draw.rectangle([bar_x0, y + 17, bar_x1, y + 23], fill=color)
        draw.line([(right_x + right_w * row["recallPercent"] / 100, y + 10),
                   (right_x + right_w * row["recallPercent"] / 100, y + 30)], fill=color, width=4)
        draw.text((left_x + bar_w + 10, y + 8), f"{row['support']}  ({row['supportSharePercent']:.1f}%)",
                  font=small_font, fill=MUTED)
        draw.text((right_x + right_w + 12, y + 8), f"{row['recallPercent']:.1f}", font=small_font, fill=INK)

    note = "注：gnawing（4 条）、fall / seizure（0 条）样本不足，区间宽度本身说明它们不能作为结论。"
    draw.text((48, height - 46), note, font=small_font, fill=MUTED)
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
    figure_class_overview(rows, args.out / "fig-class-overview.png", args.font)
    if matrix:
        figure_confusion(matrix, classes, args.out / "fig-confusion.png", args.font)
    figure_motion_surface(clips, args.out / "fig-motion-surface.png", args.font)
    figure_error_by_motion(summary, args.out / "fig-error-by-motion.png", args.font)
    print(f"图输出到 {args.out}（混淆矩阵：{'用 confusion_matrix' if matrix else '缺失，未画'}）")


if __name__ == "__main__":
    main()
