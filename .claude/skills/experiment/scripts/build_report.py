#!/usr/bin/env python3
"""从作者清单生成一篇实验报告（management/experiments/<topic>/<slug>/）。

作者清单（--manifest 输入，JSON）示例——report 文字四项 / evidence 六项 / metrics / cases：

{
  "report": {
    "summary": "结论摘要（可省，省略时取 --summary 或标缺）",
    "question": "实验问题与假设",
    "limitations": "失败案例与限制",
    "conclusion": "结论与建议"
  },
  "evidence": {
    "实验类型": "性能 / 感知质量 / 正确性",
    "baseline 数值来源": "…",
    "可辨识性": "…",
    "样本量": "…",
    "失败边界": "…",
    "结论上界": "…"
  },
  "metrics": [{
    "name": "示例误差", "unit": "px", "baseline": "3", "result": "2",
    "delta": "-1", "sample_size": "20", "source": "metrics.md",
    "limitation": "不衡量语音同步"
  }],
  "metrics_json": {          // 可选：直接提供 series/tables（默认从 metrics 表自动推导）
    "series": [], "tables": []
  },
  "cases": [{
    "id": "baseline", "kind": "image", "src": "path/relative/to/repo/or/absolute",
    "source_run": "<run-id>", "input": "输入描述", "selection_reason": "选择理由"
  }],
  "environment": {           // 环境段（「实验设置与环境」），键值自由，缺 required_env_keys 中的键 → incomplete
    "模型": "…", "数据集": "…", "配置": "…", "运行时间戳": "…", "执行入口": "…", "随机种子": "42"
  }
}

行为：
- 不覆盖已有报告（--force 显式覆盖）
- 缺失项写进 manifest.diagnostics，报告保持 incomplete（由后端按同规则推导）
- 案例图片复制进 assets/ 并计算 sha256；case 缺文件 → diagnostics 记缺失，不中断

与 server/parsers/experiments_parser.py 的常量保持同步（章节名 / frontmatter 必填 / evidence 六项）。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

# ==== 与 server/parsers/experiments_parser.py 同步的常量 ====
SECTIONS = ["结论摘要", "实验问题与假设", "实验设置与环境", "指标结果", "案例展示", "失败案例与限制", "结论与建议", "产物来源"]
REQUIRED_FRONTMATTER = ["title", "date", "run_id", "status", "verdict", "summary", "source"]
EVIDENCE_KEYS = ["实验类型", "baseline 数值来源", "可辨识性", "样本量", "失败边界", "结论上界"]
METRIC_FIELDS = ["name", "unit", "baseline", "result", "delta", "sample_size", "source", "limitation"]
CASE_FIELDS = ["id", "kind", "src", "source_run", "input", "selection_reason"]
REQUIRED_ENV_KEYS = ["模型", "数据集", "配置", "运行时间戳", "执行入口"]
STATUS_ENUM = ["complete", "partial", "failed"]
VERDICT_ENUM = ["improved", "no-gain", "worse", "inconclusive"]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
SEGMENT_RE = re.compile(r'^[^/\\\x00-\x1f\x7f]+$')


def repo_root():
    """脚本 self-locating：.agents/skills/experiment/scripts/build_report.py 上溯 5 级到仓库根
    （与 management skill 脚本的 Path(__file__).parents[4] 同深度）。"""
    d = os.path.abspath(__file__)
    for _ in range(5):
        d = os.path.dirname(d)
    return d


def load_manifest_input(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("manifest 输入必须是 JSON 对象")
    return data


def resolve_src(src):
    """案例 src：绝对路径直接用，否则相对仓库根。返回 (路径, 是否存在)。"""
    if os.path.isabs(src):
        return src, os.path.isfile(src)
    full = os.path.join(repo_root(), src)
    return full, os.path.isfile(full)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_report_md(meta, author, env, diagnostics):
    lines = ["---"]
    for k in REQUIRED_FRONTMATTER:
        v = meta.get(k, "")
        lines.append(f'{k}: {json.dumps(str(v), ensure_ascii=False)}')
    lines.append("---")
    lines.append("")

    def section(title, body):
        lines.append(f"## {title}")
        lines.append("")
        if body and str(body).strip():
            lines.append(str(body).strip())
        else:
            lines.append(f"（缺失：{title}未提供，待补充。）")
        lines.append("")

    section("结论摘要", meta.get("summary", ""))
    section("实验问题与假设", author.get("question", ""))
    lines.append("## 实验设置与环境")
    lines.append("")
    if env:
        for k, v in env.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("（缺失：环境记录未提供。）")
    missing_env = [k for k in REQUIRED_ENV_KEYS if not str(env.get(k, "")).strip()]
    if missing_env:
        lines.append(f"（缺失环境项：{'、'.join(missing_env)}）")
    lines.append("")
    section("指标结果", "见下方指标表；单位、样本量与局限见 manifest 的 metrics 条目。")
    section("案例展示", "案例由作者按选样规则显式选择，见 manifest 的 cases 条目。")
    section("失败案例与限制", author.get("limitations", ""))
    section("结论与建议", author.get("conclusion", ""))
    src = meta.get("source", "")
    section("产物来源", f"- run 产物：{src}\n（详细来源见 manifest 各条目的 source 字段。）" if src else "")
    if diagnostics:
        lines.append("<!-- diagnostics（生成器写入，勿手改）：")
        for d in diagnostics:
            lines.append(f"  - {d}")
        lines.append("-->")
    return "\n".join(lines) + "\n"


def derive_metrics_json(metrics, provided):
    if provided:
        ok = isinstance(provided, dict) and "series" in provided and "tables" in provided
        return provided if ok else None
    # 从 metrics 表自动推导：name 为列，每条 metric 一行（baseline/result 两列）
    if not metrics:
        return {"series": [], "tables": []}
    columns = ["指标", "单位", "baseline", "结果", "变化", "样本量"]
    rows = [[m.get("name", ""), m.get("unit", ""), m.get("baseline", ""),
             m.get("result", ""), m.get("delta", ""), m.get("sample_size", "")] for m in metrics]
    return {"series": [], "tables": [{"title": "指标对比", "columns": columns, "rows": rows}]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, help="实验主题目录名")
    ap.add_argument("--slug", required=True, help="报告目录名，如 20261102-myrun")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--run-id", required=True, dest="run_id")
    ap.add_argument("--status", required=True, choices=STATUS_ENUM)
    ap.add_argument("--verdict", required=True, choices=VERDICT_ENUM)
    ap.add_argument("--title", required=True, help="实验主题：对照方案与评估目标")
    ap.add_argument("--source", required=True, help="run 产物路径（仓库相对）")
    ap.add_argument("--manifest", required=True, help="作者清单 JSON 路径")
    ap.add_argument("--change", default="", help="关联 openspec change（可选）")
    ap.add_argument("--force", action="store_true", help="覆盖已有报告")
    args = ap.parse_args()

    diagnostics = []
    for label, seg in (("topic", args.topic), ("slug", args.slug)):
        if not SEGMENT_RE.match(seg) or seg in {".", ".."}:
            ap.error(f"{label} 含非法字符：{seg!r}")

    author_input = load_manifest_input(args.manifest)
    author = author_input.get("report", {}) or {}
    evidence = author_input.get("evidence", {}) or {}
    metrics = author_input.get("metrics", []) or []
    cases_in = author_input.get("cases", []) or []
    env = author_input.get("environment", {}) or {}

    meta = {
        "title": args.title, "date": args.date, "run_id": args.run_id,
        "status": args.status, "verdict": args.verdict,
        "summary": author.get("summary", ""), "source": args.source,
    }
    if args.change:
        meta["change"] = args.change

    root = repo_root()
    report_dir = os.path.join(root, "management", "experiments", args.topic, args.slug)
    if os.path.exists(report_dir) and not args.force:
        print(f"报告已存在：{report_dir}（--force 覆盖）", file=sys.stderr)
        return 2
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)
    os.makedirs(os.path.join(report_dir, "assets"), exist_ok=True)

    # 案例：复制图片 + sha256
    cases_out = []
    for c in cases_in:
        missing = [f for f in CASE_FIELDS if not str(c.get(f, "")).strip()]
        if missing:
            diagnostics.append(f"case 缺字段 {c.get('id', '?')}: {'、'.join(missing)}")
            continue
        if c.get("kind") != "image":
            diagnostics.append(f"case {c['id']}: 暂不支持 kind={c.get('kind')}")
            continue
        full, exists = resolve_src(c["src"])
        if not exists:
            diagnostics.append(f"case {c['id']}: 文件不存在 {c['src']}")
            continue
        ext = os.path.splitext(full)[1].lower()
        if ext not in IMAGE_EXTS:
            diagnostics.append(f"case {c['id']}: 扩展名 {ext} 不在白名单")
            continue
        digest = sha256_of(full)
        dest = os.path.join(report_dir, "assets", f"{digest}{ext}")
        shutil.copyfile(full, dest)
        cases_out.append({
            "id": c["id"], "kind": "image", "src": f"assets/{digest}{ext}",
            "source_run": c["source_run"], "input": c["input"],
            "selection_reason": c["selection_reason"], "sha256": digest,
        })

    # evidence / metrics 校验
    for k in EVIDENCE_KEYS:
        if not str(evidence.get(k, "")).strip():
            diagnostics.append(f"evidence 缺项：{k}")
    metrics_out = []
    for m in metrics:
        missing = [f for f in METRIC_FIELDS if not str(m.get(f, "")).strip()]
        if missing:
            diagnostics.append(f"metric {m.get('name', '?')} 缺字段：{'、'.join(missing)}")
            continue
        metrics_out.append({f: str(m[f]) for f in METRIC_FIELDS})
    if not metrics_out:
        diagnostics.append("无有效 metric 条目")
    if not cases_out:
        diagnostics.append("无有效案例（案例须作者显式选择）")
    for k in REQUIRED_ENV_KEYS:
        if not str(env.get(k, "")).strip():
            diagnostics.append(f"环境缺项：{k}")

    # 与后端同规则：frontmatter 必填空值也算缺失（含 summary 空）
    for k in REQUIRED_FRONTMATTER:
        if not str(meta.get(k, "")).strip():
            diagnostics.append(f"frontmatter 缺失/为空：{k}")

    metrics_json = derive_metrics_json(metrics_out, author_input.get("metrics_json"))
    if metrics_json is None:
        diagnostics.append("metrics_json 结构非法（须含 series 与 tables）")
        metrics_json = {"series": [], "tables": []}

    report_md = build_report_md(meta, author, env, diagnostics)
    with open(os.path.join(report_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
    with open(os.path.join(report_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_json, f, ensure_ascii=False, indent=2)
        f.write("\n")
    manifest = {"evidence": {k: str(evidence.get(k, "")) for k in EVIDENCE_KEYS},
                "metrics": metrics_out, "cases": cases_out, "diagnostics": diagnostics}
    with open(os.path.join(report_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    incomplete = "是" if diagnostics else "否"
    print(f"报告生成：{os.path.relpath(report_dir, root)}")
    print(f"incomplete 推导：{incomplete}（{len(diagnostics)} 项缺失）")
    for d in diagnostics:
        print(f"  - {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
