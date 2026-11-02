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
    assert "结论摘要" in detail["content"]
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
    assert len(entry["problems"]) >= 10


def test_asset_traversal_rejected():
    assert client.get("/api/management/experiments/t/s/assets/..%2F..%2F..%2Fconfig.py").status_code in (400, 404)
    assert client.get("/api/management/experiments/t/s/assets/evil.exe").status_code == 404


def test_unknown_report_404():
    assert client.get("/api/management/experiments/no/such").status_code == 404
