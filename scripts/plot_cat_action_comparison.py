#!/usr/bin/env python3
"""Render the six-model cat action test comparison as a PNG table."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

MODELS = [
    ("videomaev2_b", "VideoMAEv2-B"),
    ("x3d_s", "X3D-S"),
    ("slowfast_r50", "SlowFast-R50"),
    ("tsm_r50", "TSM-R50"),
    ("uniformerv2_b", "UniFormerV2-B"),
    ("tsn_r50", "TSN-R50"),
]
SELECTED = "videomaev2_b"

INK = "#1B2430"
MUTED = "#5B6673"
RULE = "#DCE2E7"
BAND = "#EAF2F4"
ACCENT = "#1D5B6E"
HEADER_RULE = "#9AA7B1"


def load(results: Path, name: str) -> dict:
    state = json.loads((results / name / "run_status.json").read_text(encoding="utf-8"))
    val = state["best_val_metrics"]
    test = state["test_metrics"]
    return {
        "val_f1": val["macro_f1_percent"],
        "top1": test["top1_acc_percent"],
        "test_f1": test["macro_f1_percent"],
        "balanced": test["balanced_acc_percent"],
        "abnormal": test["abnormal"]["recall_percent"],
        "miss": 100.0 - test["top1_acc_percent"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=str(ROOT / "results/training/cat_action_v1"))
    parser.add_argument("--out", default=str(
        ROOT / "results/training/cat_action_v1/model_comparison.png"))
    args = parser.parse_args()

    rows = []
    for name, label in MODELS:
        data = load(Path(args.results), name)
        data.update(name=name, label=label)
        rows.append(data)

    columns = [
        ("验证 macro-F1", "val_f1", "max"),
        ("测试 top-1", "top1", "max"),
        ("测试 macro-F1", "test_f1", "max"),
        ("balanced acc", "balanced", "max"),
        ("abnormal 召回", "abnormal", "max"),
        ("总体漏检率", "miss", "min"),
    ]

    plt.rcParams["font.family"] = "Microsoft YaHei"
    plt.rcParams["axes.unicode_minus"] = False
    fig = plt.figure(figsize=(12.8, 6.6), dpi=200, facecolor="white")
    ax = fig.add_axes([0.05, 0.13, 0.90, 0.66])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.05, 0.935, "猫动作识别六模型测试集对比", fontsize=23, fontweight="bold",
             color=INK, ha="left")
    fig.text(0.05, 0.878, "自然分布测试集 442 条 · 区间级指标 · 数值为百分比",
             fontsize=11.5, color=MUTED, ha="left")

    xs = [0.0, 0.285, 0.425, 0.565, 0.700, 0.835, 0.995]
    y_header = 0.925
    ax.text(xs[0], y_header, "模型", fontsize=12.5, fontweight="bold",
            color=MUTED, va="center", ha="left")
    for x, (title, _, _) in zip(xs[1:], columns):
        ax.text(x, y_header, title, fontsize=12.5, fontweight="bold",
                color=MUTED, va="center", ha="right")
    ax.plot([0, 1], [0.865, 0.865], color=HEADER_RULE, linewidth=1.4,
            solid_capstyle="butt")

    best = {}
    for _, key, mode in columns:
        values = [row[key] for row in rows]
        best[key] = max(values) if mode == "max" else min(values)

    y = 0.760
    step = 0.132
    for row in rows:
        if row["name"] == SELECTED:
            ax.add_patch(Rectangle((0, y - step / 2), 1, step,
                                   facecolor=BAND, edgecolor="none", zorder=0))
        is_selected = row["name"] == SELECTED
        ax.text(xs[0], y, row["label"], fontsize=13.5,
                fontweight="bold" if is_selected else "normal",
                color=ACCENT if is_selected else INK, va="center", ha="left")
        for x, (_, key, _) in zip(xs[1:], columns):
            value = row[key]
            is_best = abs(value - best[key]) < 1e-9
            ax.text(x, y, f"{value:.2f}", fontsize=13.5,
                    fontweight="bold" if is_best else "normal",
                    color=ACCENT if is_best else INK, va="center", ha="right")
        ax.plot([0, 1], [y - step / 2, y - step / 2], color=RULE,
                linewidth=0.7, zorder=1)
        y -= step

    fig.text(0.05, 0.075,
             "加粗为该列最优；高亮行为验证集选出的模型，测试指标在排名冻结后运行。",
             fontsize=10, color=MUTED, ha="left")
    fig.text(0.05, 0.042,
             "总体漏检率 = 1 − top-1，为区间级错误率，不是连续视频的事件级漏检率；"
             "abnormal 测试样本 18 条，toileting 7 条。",
             fontsize=10, color=MUTED, ha="left")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
