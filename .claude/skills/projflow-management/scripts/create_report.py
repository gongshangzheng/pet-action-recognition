#!/usr/bin/env python3
"""Create a report file (daily / weekly / monthly).

Self-locating; argparse; identical file used in infraredComp and ProjFlow.

    daily:   management/daily/{YYYY}/{MM}/{DD}-{author}.md     (--date YYYY-MM-DD)
    weekly:  management/weekly/{YYYY}/W{NN}-{author}.md         (--year --week)
    monthly: management/monthly/{YYYY}/{MM}-{author}.md         (--year --month)

Usage:
    python3 create_report.py --type daily --author zhangsan --date 2026-07-11
    python3 create_report.py --type weekly --author zhangsan --year 2026 --week 28
    python3 create_report.py --type monthly --author zhangsan --year 2026 --month 07
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

TYPE_TITLE = {"daily": "日报", "weekly": "周报", "monthly": "月报"}
WORK_HEADER = {"daily": "今日工作", "weekly": "本周工作", "monthly": "本月工作"}
PLAN_HEADER = {"daily": "明日计划", "weekly": "下周计划", "monthly": "下月计划"}


def title_line(rtype: str, author: str, *, date, year, week, month) -> str:
    if rtype == "daily":
        y, m, d = date.split("-")
        return f"# {TYPE_TITLE[rtype]} — {author} — {y}-{m}-{d}"
    if rtype == "weekly":
        w = (week or "").lstrip("Ww")
        return f"# {TYPE_TITLE[rtype]} — {author} — {year} 第 {int(w)} 周"
    return f"# {TYPE_TITLE[rtype]} — {author} — {year}-{month}"


def build_body(rtype: str) -> str:
    return (
        f"\n## {WORK_HEADER[rtype]}\n\n-\n"
        f"\n## {PLAN_HEADER[rtype]}\n\n-\n"
        f"\n## 备注\n\n无\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", required=True, choices=["daily", "weekly", "monthly"])
    ap.add_argument("--author", required=True)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (daily)")
    ap.add_argument("--year", default=None)
    ap.add_argument("--week", default=None, help="week number (weekly)")
    ap.add_argument("--month", default=None, help="MM (monthly)")
    args = ap.parse_args()

    path = mgmt_io.report_path(
        args.type, args.author,
        date=args.date, year=args.year, week=args.week, month=args.month,
    )
    if path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} already exists (use update_report.py to edit)")

    title = title_line(args.type, args.author,
                       date=args.date, year=args.year, week=args.week, month=args.month)
    text = title + "\n" + build_body(args.type)
    mgmt_io.write_text(path, text)
    print(f"✓ created {args.type} report {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
