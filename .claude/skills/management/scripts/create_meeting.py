#!/usr/bin/env python3
"""Create a meeting minutes file management/docs/meetings/{date}.md.

Self-locating; argparse; identical file used in upstream and downstream repos.

Usage:
    python3 create_meeting.py --date 2026-07-11 \\
        --participants "张三、李四" --recorder 张三 --topics "进度回顾,方案讨论" \\
        --decision "确认轮廓提取用 sobel" --todo "张三:跑 CRF 扫描"
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

TEMPLATE = """# 会议纪要 — {date}

## 基本信息

- 参会人：{participants}
- 记录人：{recorder}
- 时间：{date}

## 议题

{topics}

## 讨论内容

{discussion}

## 决议

{decisions}

## 待办

{todos}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--participants", required=True)
    ap.add_argument("--recorder", required=True)
    ap.add_argument("--topics", default="", help="comma-separated agenda items")
    ap.add_argument("--decision", default=None, help="a 决议 bullet (use --append-decision later for more)")
    ap.add_argument("--todo", default=None, help="a 待办 item (owner:action)")
    args = ap.parse_args()

    path = mgmt_io.meeting_path(args.date)
    if path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} already exists (use update_meeting.py to edit)")

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    topics_block = "\n".join(f"{i}. {t}" for i, t in enumerate(topics, 1)) or "- "
    discussion = "\n\n".join(f"### {t}\n\n..." for t in topics) or "-"
    decisions = f"- {args.decision}" if args.decision else "无"
    todos = f"- [ ] {args.todo}" if args.todo else "- "

    text = TEMPLATE.format(
        date=args.date, participants=args.participants, recorder=args.recorder,
        topics=topics_block, discussion=discussion, decisions=decisions, todos=todos,
    )
    mgmt_io.write_text(path, text)
    print(f"✓ created meeting {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
