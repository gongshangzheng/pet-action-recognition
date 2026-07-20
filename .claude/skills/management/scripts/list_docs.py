#!/usr/bin/env python3
"""List all wiki docs in management/docs/ with frontmatter metadata.

Usage:
    python3 list_docs.py                # table view
    python3 list_docs.py --slug xxx     # single doc detail (frontmatter + body)
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, body) from YAML frontmatter. Minimal parser — no PyYAML dep."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("---", 3)
    if end < 0:
        return meta, text
    fm = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")
    for line in fm.splitlines():
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        meta[key] = val
    return meta, body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", default=None, help="show single doc detail")
    args = ap.parse_args()

    d = mgmt_io.docs_dir()
    if not d.is_dir():
        print("(no docs directory)")
        return 0

    if args.slug:
        path = mgmt_io.doc_path(args.slug)
        if not path.is_file():
            sys.exit(f"error: {mgmt_io.rel(path)} not found")
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        print(f"slug:    {args.slug}")
        for k, v in meta.items():
            print(f"{k:8s}: {v}")
        print("---")
        print(body)
        return 0

    files = sorted(f for f in os.listdir(d) if f.endswith(".md"))
    if not files:
        print("(no docs)")
        return 0

    print(f"{'slug':<30} {'title':<30} {'author':<12} {'date':<12} tags")
    print("-" * 100)
    for fname in files:
        slug = fname[:-3]
        text = (d / fname).read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        title = str(meta.get("title", ""))[:28]
        author = str(meta.get("author", ""))[:10]
        date = str(meta.get("date", ""))[:10]
        tags = meta.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        print(f"{slug:<30} {title:<30} {author:<12} {date:<12} {tags_str}")
    print(f"\n{len(files)} doc(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
