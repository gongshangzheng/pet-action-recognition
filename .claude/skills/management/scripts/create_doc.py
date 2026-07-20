#!/usr/bin/env python3
"""Create a wiki-style documentation file management/docs/{slug}.md.

Generates YAML frontmatter + body scaffold. Refuses to overwrite.

Usage:
    python3 create_doc.py --slug jwt-auth-guide --title "JWT 认证指南" \\
        --author 张三 --tags "auth,jwt,安全" --summary "JWT token 的生成、验证与刷新流程"
    python3 create_doc.py --slug api-design --title "API 设计规范" --author 汤问
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

TEMPLATE = """---
title: {title}
author: {author}
date: {date}
tags: [{tags}]
summary: {summary}
---

## 概述

{summary}

## 正文

"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="filename without .md (letters/digits/_/-)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--tags", default="", help="comma-separated tags")
    ap.add_argument("--summary", default="")
    ap.add_argument("--date", default=mgmt_io.TODAY, help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    path = mgmt_io.doc_path(args.slug)
    if path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} already exists (use update_doc.py to edit)")

    tags = ", ".join(t.strip() for t in args.tags.split(",") if t.strip())
    text = TEMPLATE.format(
        title=args.title,
        author=args.author,
        date=args.date,
        tags=tags,
        summary=args.summary,
    )
    mgmt_io.write_text(path, text)
    print(f"✓ created doc {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
