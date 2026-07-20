#!/usr/bin/env python3
"""Update a wiki doc's frontmatter fields or append body content.

Supports:
  --title       replace title
  --author      replace author
  --tags        replace tags (comma-separated)
  --summary     replace summary
  --append      append text to end of body

Usage:
    python3 update_doc.py --slug api-design-conventions --tags "api,rest,规范,后端"
    python3 update_doc.py --slug api-design-conventions --append "\\n## 参考资料\\n\\n- ..."
    python3 update_doc.py --slug api-design-conventions --summary "新的摘要"
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def replace_fm_field(text: str, key: str, value: str) -> str:
    """Replace a YAML frontmatter field value. Assumes text starts with ---."""
    pattern = rf"^({re.escape(key)}\s*:\s*).*$"
    replaced, n = re.subn(pattern, rf"\g<1>{value}", text, count=1, flags=re.MULTILINE)
    if n == 0:
        end = text.find("---", 3)
        if end < 0:
            sys.exit(f"error: no frontmatter found in doc")
        replaced = text[:end] + f"{key}: {value}\n" + text[end:]
    return replaced


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="doc slug (filename without .md)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--author", default=None)
    ap.add_argument("--tags", default=None, help="comma-separated tags (replaces existing)")
    ap.add_argument("--summary", default=None)
    ap.add_argument("--append", default=None, help="text to append to end of body")
    args = ap.parse_args()

    path = mgmt_io.doc_path(args.slug)
    text = mgmt_io.read_text(path)

    changed = False

    if args.title is not None:
        text = replace_fm_field(text, "title", args.title)
        print(f"✓ title -> {args.title}")
        changed = True
    if args.author is not None:
        text = replace_fm_field(text, "author", args.author)
        print(f"✓ author -> {args.author}")
        changed = True
    if args.tags is not None:
        tags_str = "[" + ", ".join(t.strip() for t in args.tags.split(",") if t.strip()) + "]"
        text = replace_fm_field(text, "tags", tags_str)
        print(f"✓ tags -> {tags_str}")
        changed = True
    if args.summary is not None:
        text = replace_fm_field(text, "summary", args.summary)
        print(f"✓ summary -> {args.summary}")
        changed = True
    if args.append is not None:
        if not text.endswith("\n"):
            text += "\n"
        text += args.append
        if not text.endswith("\n"):
            text += "\n"
        print(f"✓ appended {len(args.append)} chars")
        changed = True

    if not changed:
        print("(no changes)")
        return 0

    mgmt_io.write_text(path, text)
    print(f"({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
