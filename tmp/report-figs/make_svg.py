"""一次性探针：把报告表格里的数字画成横向分组条形 SVG（环境无 matplotlib）。"""
import hashlib
import os
import sys

FONT = "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"


def grouped_bars(path, title, categories, series, max_value=100.0):
    """series: [(name, color, [values])]；values 与 categories 等长，单位 %。"""
    rowh = 34
    left, right, top = 190, 70, 64
    width = 860
    height = top + rowh * len(categories) + 48
    plot_w = width - left - right
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
           f'<text x="{left}" y="30" font-size="17" fill="#111">{title}</text>']
    lx = left
    for name, color, _ in series:
        out.append(f'<rect x="{lx}" y="42" width="12" height="12" fill="{color}"/>')
        out.append(f'<text x="{lx + 18}" y="53" font-size="13" fill="#333">{name}</text>')
        lx += 18 + len(name) * 13 + 24
    for i, cat in enumerate(categories):
        y = top + i * rowh
        out.append(f'<text x="{left - 12}" y="{y + 20}" font-size="13" fill="#333" text-anchor="end">{cat}</text>')
        for j, (_, color, values) in enumerate(series):
            v = values[i]
            bar_h = 11
            bar_y = y + 4 + j * (bar_h + 3)
            w = max(1.0, plot_w * v / max_value)
            out.append(f'<rect x="{left}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" fill="{color}"/>')
            out.append(f'<text x="{left + w + 6:.1f}" y="{bar_y + bar_h - 1}" font-size="11" fill="#555">{v:.1f}</text>')
    axis_x = left + plot_w
    out.append(f'<line x1="{axis_x}" y1="{top - 4}" x2="{axis_x}" y2="{height - 32}" stroke="#d0d0d0"/>')
    out.append(f'<text x="{axis_x}" y="{height - 14}" font-size="11" fill="#777" text-anchor="end">单位：%</text>')
    out.append('</svg>')
    data = "\n".join(out).encode("utf-8")
    name = hashlib.sha256(data).hexdigest() + ".svg"
    target = os.path.join(path, name)
    try:
        with open(target, "wb") as f:
            f.write(data)
    except OSError as exc:
        raise SystemExit(f"写入失败：{target}: {exc}")
    return name


if __name__ == "__main__":
    outdir = sys.argv[1]
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"创建目录失败：{outdir}: {exc}")
    a = grouped_bars(
        outdir,
        "七类区间基线（2026-10）：六个模型测试集 top-1 与 macro-F1",
        ["VideoMAEv2-B", "X3D-S", "SlowFast-R50", "TSM-R50", "UniFormerV2-B", "TSN-R50"],
        [("top-1", "#2f6fb5", [81.90, 80.09, 77.38, 79.19, 77.83, 72.85]),
         ("macro-F1", "#d98a2b", [67.66, 69.02, 63.10, 61.75, 56.70, 57.51])],
    )
    b = grouped_bars(
        outdir,
        "七类逐类召回（测试集 442 条）：TSM-R50 与 VideoMAEv2-B",
        ["activity", "eating", "drinking", "prolonged_stationary", "grooming", "toileting", "abnormal"],
        [("TSM-R50", "#2f6fb5", [86.72, 84.44, 61.54, 81.94, 5.56, 100.00, 38.89]),
         ("VideoMAEv2-B", "#d98a2b", [91.02, 86.67, 61.54, 77.78, 38.89, 42.86, 44.44])],
    )
    print(os.path.join(outdir, a))
    print(os.path.join(outdir, b))
