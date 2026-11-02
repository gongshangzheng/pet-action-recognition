"""实验报告 API 对拍测试：后端解析推导必须与生成脚本（.agents/skills/experiment/scripts/build_report.py）产出一致。"""
import importlib.util
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

_SPEC = importlib.util.spec_from_file_location(
    "build_report",
    os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "experiment", "scripts", "build_report.py"),
)
build_report = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_report)

from server.main import app  # noqa: E402

client = TestClient(app)


def _run_builder(tmp_path, slug, manifest, extra=()):
    manifest_path = tmp_path / f"{slug}-input.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    argv = [
        "build_report.py", "--topic", "t", "--slug", slug, "--date", "2026-11-02",
        "--run-id", "r1", "--status", "complete", "--verdict", "inconclusive",
        "--title", "对拍：标题格式", "--source", "evaluation/results/x.json",
        "--manifest", str(manifest_path), "--force", *extra,
    ]
    saved = sys.argv
    sys.argv = argv
    try:
        rc = build_report.main()
    finally:
        sys.argv = saved
    assert rc == 0


def _case_image(tmp_path, name, rgb):
    """最小 PNG（8x8 纯色）。"""
    import struct, zlib
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(rgb) * 8 for _ in range(8))
    p = tmp_path / name
    with open(p, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return str(p)


def test_complete_report_roundtrip(tmp_path):
    img = _case_image(tmp_path, "ok.png", (30, 144, 255))
    manifest = {
        "report": {"summary": "链路跑通；延迟数字无对照意义", "question": "q", "limitations": "l", "conclusion": "c"},
        "evidence": {k: "v" for k in build_report.EVIDENCE_KEYS},
        "metrics": [{f: "v" for f in build_report.METRIC_FIELDS} | {"name": "m1"}],
        "cases": [{"id": "c1", "kind": "image", "src": img,
                   "source_run": "r1", "input": "in", "selection_reason": "why"}],
        "environment": {k: "v" for k in build_report.REQUIRED_ENV_KEYS},
    }
    _run_builder(tmp_path, "20261102-ok", manifest)

    resp = client.get("/api/management/experiments")
    assert resp.status_code == 200
    data = resp.json()
    entry = next(r for r in data["reports"] if r["topic"] == "t" and r["slug"] == "20261102-ok")
    assert entry["incomplete"] is False
    assert entry["problems"] == []

    detail = client.get("/api/management/experiments/t/20261102-ok").json()
    assert detail["incomplete"] is False
    # 新模板：叙述字段映射（question→problem，conclusion→结论与下一步）
    assert "背景与目标" in detail["content"]
    assert "结论与下一步" in detail["content"]
    assert detail["manifest"]["cases"][0]["sha256"]
    asset = client.get(f"/api/management/experiments/t/20261102-ok/assets/{detail['manifest']['cases'][0]['src'].split('/')[1]}")
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"


def test_broken_case_marks_incomplete(tmp_path):
    import shutil
    shutil.rmtree("management/experiments/t", ignore_errors=True)
    manifest = {
        "report": {"summary": "s", "question": "q", "limitations": "l", "conclusion": "c"},
        "evidence": {k: "v" for k in build_report.EVIDENCE_KEYS},
        "metrics": [{f: "v" for f in build_report.METRIC_FIELDS} | {"name": "m1"}],
        "cases": [{"id": "gone", "kind": "image", "src": str(tmp_path / "nope.png"),
                   "source_run": "r1", "input": "in", "selection_reason": "why"}],
        "environment": {k: "v" for k in build_report.REQUIRED_ENV_KEYS},
    }
    _run_builder(tmp_path, "20261102-broken", manifest)

    entry = next(r for r in client.get("/api/management/experiments").json()["reports"]
                 if r["slug"] == "20261102-broken")
    assert entry["incomplete"] is True
    # 生成侧把缺失 case 拒收（cases 空），后端按「无有效案例」推导 incomplete
    assert any("案例" in p for p in entry["problems"])
    detail = client.get("/api/management/experiments/t/20261102-broken").json()
    assert detail["manifest"]["diagnostics"] and any("文件不存在" in d for d in detail["manifest"]["diagnostics"])


def test_empty_manifest_draft_is_incomplete(tmp_path):
    _run_builder(tmp_path, "20261102-empty", {"report": {}, "evidence": {}, "metrics": [], "cases": []})
    entry = next(r for r in client.get("/api/management/experiments").json()["reports"]
                 if r["slug"] == "20261102-empty")
    assert entry["incomplete"] is True
    assert len(entry["problems"]) >= 8  # frontmatter/evidence/metrics/cases/环境/模板


def test_asset_traversal_rejected():
    assert client.get("/api/management/experiments/t/s/assets/..%2F..%2F..%2Fconfig.py").status_code in (400, 404)
    assert client.get("/api/management/experiments/t/s/assets/evil.exe").status_code == 404


def test_unknown_report_404():
    assert client.get("/api/management/experiments/no/such").status_code == 404


def _narrative_manifest(tmp_path):
    img = _case_image(tmp_path, "n.png", (10, 200, 10))
    return {
        "report": {
            "summary": "s",
            "background": "背景：验证链路。",
            "problem": "当前问题：结果能否复现。",
            "design": "设计：两次同配置运行对照。",
            "analysis": "分析：两次 accuracy 均为 0.93，复现差 0。",
            "conclusion": "结论：链路可复现。",
            "limitations": "局限：mock 数据，不构成质量结论。",
        },
        "evidence": {k: "v" for k in build_report.EVIDENCE_KEYS},
        "metrics": [{f: "v" for f in build_report.METRIC_FIELDS} | {"name": "m1"}],
        "cases": [{"id": "c1", "kind": "image", "src": img,
                   "source_run": "r1", "input": "in", "selection_reason": "why"}],
        "environment": {k: "v" for k in build_report.REQUIRED_ENV_KEYS},
    }


def test_narrative_template_roundtrip(tmp_path):
    _run_builder(tmp_path, "20261102-narrative", _narrative_manifest(tmp_path))
    entry = next(r for r in client.get("/api/management/experiments").json()["reports"]
                 if r["slug"] == "20261102-narrative")
    assert entry["incomplete"] is False
    assert entry.get("template") == "narrative"
    detail = client.get("/api/management/experiments/t/20261102-narrative").json()
    assert detail["template"] == "narrative"
    assert "背景与目标" in detail["content"]
    assert "结论与下一步" in detail["content"]
    assert "附录：配置与完整数据" in detail["content"]


def test_legacy_template_still_valid(tmp_path):
    import shutil
    shutil.rmtree("management/experiments/t", ignore_errors=True)
    # 旧八章清单（question/limitations）：生成器旧字段别名 → 新模板；再手工改写为旧八章验证 legacy 识别
    manifest = _narrative_manifest(tmp_path)
    manifest["report"] = {"summary": "s", "question": "q", "limitations": "l", "conclusion": "c"}
    _run_builder(tmp_path, "20261102-legacy", manifest)
    # 生成器现已产新模板；手工把正文换成旧八章以验证后端 legacy 识别与向后兼容
    import re as _re
    report_path = "management/experiments/t/20261102-legacy/report.md"
    text = open(report_path, encoding="utf-8").read()
    body = text.split("---\n", 2)[2]
    legacy_body = """## 结论摘要

s

## 实验问题与假设

q

## 实验设置与环境

- 模型: m
- 数据集: d
- 配置: c
- 运行时间戳: t
- 执行入口: e

## 指标结果

见 manifest。

## 案例展示

见 manifest。

## 失败案例与限制

l

## 结论与建议

c

## 产物来源

- run 产物：evaluation/results/x.json
"""
    open(report_path, "w", encoding="utf-8").write(text.split("---\n", 2)[0] + "---\n" + text.split("---\n", 2)[1] + "---\n" + legacy_body)
    entry = next(r for r in client.get("/api/management/experiments").json()["reports"]
                 if r["slug"] == "20261102-legacy")
    assert entry["incomplete"] is False, entry["problems"]
    assert entry.get("template") == "legacy"


def test_unmatched_template_marked_incomplete(tmp_path):
    import shutil
    shutil.rmtree("management/experiments/t", ignore_errors=True)
    _run_builder(tmp_path, "20261102-noskeleton", _narrative_manifest(tmp_path))
    report_path = "management/experiments/t/20261102-noskeleton/report.md"
    text = open(report_path, encoding="utf-8").read()
    open(report_path, "w", encoding="utf-8").write(
        text.split("---\n", 2)[0] + "---\n" + text.split("---\n", 2)[1] + "---\n\n## 随便写的一节\n\n内容。\n")
    entry = next(r for r in client.get("/api/management/experiments").json()["reports"]
                 if r["slug"] == "20261102-noskeleton")
    assert entry["incomplete"] is True
    assert any("未匹配文章模板" in p for p in entry["problems"])
