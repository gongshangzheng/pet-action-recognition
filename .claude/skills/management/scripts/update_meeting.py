#!/usr/bin/env python3
"""Update a meeting minutes file management/docs/meetings/{date}.md.

Supports:
  --participants  replace the 参会人 bullet
  --recorder      replace the 记录人 bullet
  --append-decision  append a bullet to the 决议 section
  --append-todo       append a `- [ ]` bullet to the 待办 section

Usage:
    python3 update_meeting.py --date 2026-07-11 --participants "张三、李四"
    python3 update_meeting.py --date 2026-07-11 --append-todo "张三：完成轮廓评测"
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="meeting date YYYY-MM-DD (filename stem)")
    ap.add_argument("--participants", default=None, help="replace 参会人 value")
    ap.add_argument("--recorder", default=None, help="replace 记录人 value")
    ap.add_argument("--append-decision", default=None, help="append a bullet to 决议")
    ap.add_argument("--append-todo", default=None, help="append a `- [ ]` bullet to 待办")
    args = ap.parse_args()

    path = mgmt_io.meeting_path(args.date)
    lines = mgmt_io.read_lines(path)

    if args.participants is not None:
        lines = mgmt_io.replace_bullet_field(lines, "参会人", args.participants)
        print(f"✓ 参会人 -> {args.participants}")
    if args.recorder is not None:
        lines = mgmt_io.replace_bullet_field(lines, "记录人", args.recorder)
        print(f"✓ 记录人 -> {args.recorder}")
    if args.append_decision is not None:
        lines = mgmt_io.append_to_section(lines, "## 决议", [f"- {args.append_decision}"])
        print(f"✓ 决议 += {args.append_decision!r}")
    if args.append_todo is not None:
        lines = mgmt_io.append_to_section(lines, "## 待办", [f"- [ ] {args.append_todo}"])
        print(f"✓ 待办 += {args.append_todo!r}")

    mgmt_io.write_lines(path, lines)
    print(f"({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
