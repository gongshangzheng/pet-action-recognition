#!/usr/bin/env python3
"""Validate article-note analysis structure without changing files."""
import argparse
import re
import sys
from pathlib import Path

LANES = {"background", "methodology", "experiment", "terminology", "citation", "code-analysis", "image-collection"}
REQUIRED_HEADINGS = ("## 结论", "## 证据位置", "## 不确定性与缺口", "## 给写作的建议")


def main():
    parser = argparse.ArgumentParser(description="校验 article-note 分析产物")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    root = Path(args.workspace).expanduser().resolve()
    analysis = root / "analysis"
    errors = []
    warnings = []
    if not analysis.is_dir():
        print("ERROR: missing analysis directory")
        return 1
    files = sorted(analysis.glob("*.md"))
    for path in files:
        lane = path.stem
        text = path.read_text(encoding="utf-8", errors="ignore")
        if lane not in LANES:
            warnings.append("unknown lane: %s" % path.name)
        missing = [heading for heading in REQUIRED_HEADINGS if heading not in text and lane != "image-collection"]
        for heading in missing:
            errors.append("%s missing %s" % (path.name, heading))
        if not re.search(r"证据|来源|source|raw/|页码|§", text, re.I):
            errors.append("%s has no obvious source pointer" % path.name)
    synthesis = root / "synthesis.md"
    if not synthesis.exists():
        errors.append("missing synthesis.md")
    else:
        length = len(synthesis.read_text(encoding="utf-8", errors="ignore").replace("# Synthesis", "" ).strip())
        if length > 1000:
            errors.append("synthesis.md exceeds 1000 characters")
        elif length < 20:
            warnings.append("synthesis.md is nearly empty")
    code = analysis / "code-analysis.md"
    workspace_manifest = root / "workspace.json"
    if code.exists() and workspace_manifest.exists():
        manifest = workspace_manifest.read_text(encoding="utf-8", errors="ignore")
        if '"repository"' not in manifest and '"github"' not in manifest:
            warnings.append("code-analysis.md exists but workspace manifest has no repository field")
    for item in errors:
        print("ERROR:", item)
    for item in warnings:
        print("WARNING:", item)
    if not errors:
        print("analysis validation: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
