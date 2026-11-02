"""实验报告解析器（management/experiments/<topic>/<slug>/）。

与 .agents/skills/experiment/scripts/build_report.py 的常量保持同步：
章节名 / frontmatter 必填 / evidence 六项 / metric 与 case 字段 / 环境必填键。
incomplete 推导规则两边一致（见 tests/test_experiments_api.py 的对拍断言）。
"""
import hashlib
import json
import os
import re

from server.utils.file_utils import read_file, scan_directory

SECTIONS = ["结论摘要", "实验问题与假设", "实验设置与环境", "指标结果", "案例展示", "失败案例与限制", "结论与建议", "产物来源"]
REQUIRED_FRONTMATTER = ["title", "date", "run_id", "status", "verdict", "summary", "source"]
EVIDENCE_KEYS = ["实验类型", "baseline 数值来源", "可辨识性", "样本量", "失败边界", "结论上界"]
METRIC_FIELDS = ["name", "unit", "baseline", "result", "delta", "sample_size", "source", "limitation"]
CASE_FIELDS = ["id", "kind", "src", "source_run", "input", "selection_reason"]
REQUIRED_ENV_KEYS = ["模型", "数据集", "配置", "运行时间戳", "执行入口"]
STATUS_ENUM = ("complete", "partial", "failed")
VERDICT_ENUM = ("improved", "no-gain", "worse", "inconclusive")
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
_SEGMENT_RE = re.compile(r'^[^/\\\x00-\x1f\x7f]+$')


def valid_segment(seg):
    return bool(_SEGMENT_RE.match(seg)) and seg not in {".", ".."}


def _parse_frontmatter(text):
    """返回 (meta_dict, body)；无 frontmatter 时 ({}, text)。"""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            v = v.strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            meta[k.strip()] = v
    return meta, text[end + 5:]


def _environment_missing(section_text):
    """环境段按行内清单 `- 键: 值` 检查必填键（与生成脚本 REQUIRED_ENV_KEYS 同步）。"""
    missing = []
    for key in REQUIRED_ENV_KEYS:
        found = False
        for line in section_text.splitlines():
            if line.startswith(f"- {key}:") and line[len(f"- {key}:"):].strip():
                found = True
                break
        if not found:
            missing.append(key)
    return missing


def _section(body, heading):
    marker = f"## {heading}\n"
    start = body.find(marker)
    if start < 0:
        return None
    section = body[start + len(marker):]
    end = section.find("\n## ")
    return section[:end] if end >= 0 else section


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _case_problems(report_dir, cases):
    problems = []
    if not isinstance(cases, list) or not cases:
        return ["无有效案例（案例须作者显式选择）"]
    for c in cases:
        cid = c.get("id", "?")
        for f in CASE_FIELDS:
            if not str(c.get(f, "")).strip():
                problems.append(f"case {cid} 缺字段：{f}")
        if c.get("kind") != "image":
            problems.append(f"case {cid}: 暂不支持 kind={c.get('kind')}")
            continue
        src = str(c.get("src", ""))
        parts = src.split("/")
        if len(parts) != 2 or parts[0] != "assets" or not valid_segment(parts[1]):
            problems.append(f"case {cid}: src 须为 assets/<file>（得到 {src}）")
            continue
        if os.path.splitext(parts[1])[1].lower() not in ASSET_EXTS:
            problems.append(f"case {cid}: 扩展名不在白名单")
            continue
        asset = os.path.join(report_dir, *parts)
        if not os.path.isfile(asset):
            problems.append(f"case {cid}: 文件不存在 {src}")
            continue
        want = str(c.get("sha256", "")).lower()
        if want and _sha256(asset) != want:
            problems.append(f"case {cid}: sha256 不匹配")
    return problems


def _load_json(path):
    try:
        return json.loads(read_file(path) or "null")
    except (json.JSONDecodeError, ValueError):
        return None


def report_problems(report_dir):
    """对一篇报告做完整性与 incomplete 推导，返回 (entry_fields, problems)。"""
    problems = []
    report_path = os.path.join(report_dir, "report.md")
    if not os.path.isfile(report_path):
        return None, ["缺 report.md"]

    text = read_file(report_path) or ""
    meta, body = _parse_frontmatter(text)

    for k in REQUIRED_FRONTMATTER:
        if not str(meta.get(k, "")).strip():
            problems.append(f"frontmatter 缺失/为空：{k}")
    if meta.get("status") and meta["status"] not in STATUS_ENUM:
        problems.append(f"status 非法：{meta['status']}")
    if meta.get("verdict") and meta["verdict"] not in VERDICT_ENUM:
        problems.append(f"verdict 非法：{meta['verdict']}")

    for sec in SECTIONS:
        if _section(body, sec) is None:
            problems.append(f"缺章节：{sec}")
    env_section = _section(body, "实验设置与环境")
    if env_section is not None:
        for key in _environment_missing(env_section):
            problems.append(f"环境缺项：{key}")

    manifest = _load_json(os.path.join(report_dir, "manifest.json"))
    metrics_json = _load_json(os.path.join(report_dir, "metrics.json"))

    if not isinstance(manifest, dict):
        problems.append("manifest.json 缺失或非法")
        manifest = {}
    evidence = manifest.get("evidence") or {}
    for k in EVIDENCE_KEYS:
        if not str(evidence.get(k, "")).strip():
            problems.append(f"evidence 缺项：{k}")
    metrics = manifest.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        problems.append("无有效 metric 条目")
    else:
        for m in metrics:
            for f in METRIC_FIELDS:
                if not str(m.get(f, "")).strip():
                    problems.append(f"metric {m.get('name', '?')} 缺字段：{f}")
    problems.extend(_case_problems(report_dir, manifest.get("cases")))

    if not isinstance(metrics_json, dict) or "series" not in metrics_json or "tables" not in metrics_json:
        problems.append("metrics.json 缺失或结构非法（须含 series 与 tables）")

    entry = {
        "topic": os.path.basename(os.path.dirname(report_dir)),
        "slug": os.path.basename(report_dir),
        "title": meta.get("title", ""),
        "date": meta.get("date", ""),
        "run_id": meta.get("run_id", ""),
        "status": meta.get("status", ""),
        "verdict": meta.get("verdict", ""),
        "summary": meta.get("summary", ""),
    }
    return entry, problems


def list_experiments(experiments_dir):
    """扫描两级目录，返回 {reports: [...], invalid: [...]}。"""
    reports, invalid = [], []
    if not os.path.isdir(experiments_dir):
        return {"reports": [], "invalid": []}
    for entry in sorted(os.listdir(experiments_dir)):
        topic_dir = os.path.join(experiments_dir, entry)
        if not os.path.isdir(topic_dir) or entry.startswith(".") or entry.startswith("_"):
            continue
        for slug in sorted(os.listdir(topic_dir)):
            report_dir = os.path.join(topic_dir, slug)
            if not os.path.isdir(report_dir) or slug.startswith("."):
                continue
            entry_fields, problems = report_problems(report_dir)
            if entry_fields is None:
                invalid.append({"topic": entry, "slug": slug, "missing": problems})
                continue
            entry_fields["incomplete"] = bool(problems)
            entry_fields["problems"] = problems
            reports.append(entry_fields)
    return {"reports": reports, "invalid": invalid}


def get_experiment_detail(experiments_dir, topic, slug):
    """单篇详情：frontmatter + 正文 + metrics.json + manifest + problems。"""
    if not (valid_segment(topic) and valid_segment(slug)):
        return None
    report_dir = os.path.join(experiments_dir, topic, slug)
    if not os.path.isdir(report_dir):
        return None
    entry, problems = report_problems(report_dir)
    if entry is None:
        return {"topic": topic, "slug": slug, "metadata": {}, "content": "",
                "metrics": {"series": [], "tables": []}, "manifest": {},
                "incomplete": True, "problems": problems}
    text = read_file(os.path.join(report_dir, "report.md")) or ""
    meta, body = _parse_frontmatter(text)
    metrics_json = _load_json(os.path.join(report_dir, "metrics.json"))
    manifest = _load_json(os.path.join(report_dir, "manifest.json")) or {}
    if not isinstance(metrics_json, dict):
        metrics_json = {"series": [], "tables": []}
    return {
        "metadata": meta,
        "content": body.strip(),
        "metrics": metrics_json,
        "manifest": manifest,
        "incomplete": bool(problems),
        "problems": problems,
    }


def resolve_experiment_asset(experiments_dir, topic, slug, filename):
    """解析报告资产路径（防穿越 + 白名单）；不校验存在性由调用方处理。"""
    if not (valid_segment(topic) and valid_segment(slug) and valid_segment(filename)):
        return None
    if os.path.splitext(filename)[1].lower() not in ASSET_EXTS:
        return None
    path = os.path.join(experiments_dir, topic, slug, "assets", filename)
    real = os.path.realpath(path)
    base = os.path.realpath(os.path.join(experiments_dir, topic, slug, "assets"))
    if real != base and not real.startswith(base + os.sep):
        return None
    return path
