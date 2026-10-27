#!/usr/bin/env python3
"""Validate a ProjFlow article-note Markdown file and its sidecar."""
import argparse
import json
import re
import sys
from pathlib import Path

ALLOWED_META = {"title", "author", "date", "tags", "summary", "id"}
IMAGE_RE = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text, ["missing frontmatter"]
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text, ["unterminated frontmatter"]
    metadata = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("\"'")
    return metadata, text[end + 4:], []


def main():
    parser = argparse.ArgumentParser(description="校验 article-note wiki 笔记")
    parser.add_argument("--note", required=True)
    parser.add_argument("--docs-root", default="management/docs")
    parser.add_argument("--assets-root", default="management/docs/_assets")
    args = parser.parse_args()
    note = Path(args.note).expanduser().resolve()
    docs_root = Path(args.docs_root).expanduser().resolve()
    assets_root = Path(args.assets_root).expanduser().resolve()
    errors = []
    warnings = []
    if not note.exists():
        print("ERROR: note not found")
        return 1
    text = note.read_text(encoding="utf-8", errors="ignore")
    metadata, body, fm_errors = parse_frontmatter(text)
    errors.extend(fm_errors)
    unknown = set(metadata) - ALLOWED_META
    if unknown:
        errors.append("unsupported frontmatter fields: %s" % ", ".join(sorted(unknown)))
    for key in ("title", "author", "date", "tags", "summary"):
        if key not in metadata:
            errors.append("missing frontmatter field: %s" % key)
    headings = re.findall(r"^(#{2,6})\s+(.+)$", body, re.M)
    if any(len(level) > 3 for level, _ in headings):
        errors.append("headings deeper than ### are not allowed")
    required_sections = ("论文信息", "一句话总结", "问题与动机", "方法精析", "实验与结果", "局限与启发", "术语与符号表")
    present_titles = {title.strip() for _, title in headings}
    missing_sections = [title for title in required_sections if title not in present_titles]
    if missing_sections:
        warnings.append("standard sections missing or intentionally skipped: %s" % ", ".join(missing_sections))
    # 渲染器支持 $...$ 与 $$...$$；\(...\) / \[...\] 会被 markdown 转义吃掉，属不支持的写法
    if re.search(r"\\\(|\\\[", body):
        warnings.append("found \\(...\\) or \\[...\\] delimiters; 本库只支持 $...$ 与 $$...$$")
    if "\\begin{equation" in body:
        warnings.append("found \\begin{equation}; 建议改用 $$...$$ 块级公式")
    images = IMAGE_RE.findall(body)
    for index, (alt, url) in enumerate(images, 1):
        if not url.startswith("/api/management/docs-assets/"):
            errors.append("image %d does not use absolute docs-assets URL" % index)
        if not alt:
            warnings.append("image %d has empty alt/caption" % index)
        parts = url.split("/api/management/docs-assets/", 1)[-1].split("/", 1)
        if len(parts) == 2:
            asset = assets_root / parts[0] / parts[1]
            if not asset.exists():
                errors.append("image asset missing: %s" % asset)
    numbers = []
    for alt, _ in images:
        match = re.match(r"图\s*(\d+)", alt)
        if match:
            numbers.append(int(match.group(1)))
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        errors.append("figure numbers are not continuous: %s" % numbers)
    sidecar = note.with_suffix(".json")
    if not sidecar.exists():
        errors.append("missing sidecar: %s" % sidecar)
    else:
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                errors.append("sidecar root must be an object")
        except (OSError, ValueError) as exc:
            errors.append("invalid sidecar JSON: %s" % exc)
    for target in LINK_RE.findall(body):
        candidate = docs_root / (target + ".md")
        if not candidate.exists() and not target.startswith("proj#"):
            warnings.append("internal link target not found locally: %s" % target)
    for item in errors:
        print("ERROR:", item)
    for item in warnings:
        print("WARNING:", item)
    if not errors:
        print("note validation: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
