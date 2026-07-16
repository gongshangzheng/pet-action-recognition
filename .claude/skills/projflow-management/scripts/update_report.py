#!/usr/bin/env python3
"""Update a report file (daily / weekly / monthly).

Appends work / plan bullets to the right section and can set the 备注 section.
Section names differ per type:

    daily   -> 今日工作 / 明日计划 / 备注
    weekly  -> 本周工作 / 下周计划 / 备注
    monthly -> 本月工作 / 下月计划 / 备注

Usage:
    python3 update_report.py --type daily --author zhangsan --date 2026-07-11 \\
        --append-work "完成轮廓提取 baseline" --append-plan "跑 AV1 CRF 扫描"
    python3 update_report.py --type weekly --author zhangsan --year 2026 --week 28 \\
        --append-work "OSU 数据集落地"
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

WORK_SECTION = {
    "daily": "## 今日工作",
    "weekly": "## 本周工作",
    "monthly": "## 本月工作",
}
PLAN_SECTION = {
    "daily": "## 明日计划",
    "weekly": "## 下周计划",
    "monthly": "## 下月计划",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", required=True, choices=["daily", "weekly", "monthly"])
    ap.add_argument("--author", required=True, help="english id")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (daily)")
    ap.add_argument("--year", default=None)
    ap.add_argument("--week", default=None, help="week number, e.g. 28 or W28 (weekly)")
    ap.add_argument("--month", default=None, help="MM (monthly)")
    ap.add_argument("--append-work", default=None, help="append a bullet to the work section")
    ap.add_argument("--append-plan", default=None, help="append a bullet to the plan section")
    ap.add_argument("--note", default=None, help="replace the 备注 section body")
    args = ap.parse_args()

    path = mgmt_io.report_path(
        args.type, args.author,
        date=args.date, year=args.year, week=args.week, month=args.month,
    )
    lines = mgmt_io.read_lines(path)

    if args.append_work is not None:
        lines = mgmt_io.append_to_section(lines, WORK_SECTION[args.type], [f"- {args.append_work}"])
        print(f"✓ {WORK_SECTION[args.type]} += {args.append_work!r}")
    if args.append_plan is not None:
        lines = mgmt_io.append_to_section(lines, PLAN_SECTION[args.type], [f"- {args.append_plan}"])
        print(f"✓ {PLAN_SECTION[args.type]} += {args.append_plan!r}")
    if args.note is not None:
        # rewrite the 备注 section: drop existing body, insert note
        idx = mgmt_io.find_header_line(lines, "## 备注")
        if idx < 0:
            sys.exit("error: ## 备注 section not found")
        end = mgmt_io.section_end(lines, idx)
        lines = lines[: idx + 1] + ["", args.note, ""] + lines[end:]
        print(f"✓ 备注 updated")

    mgmt_io.write_lines(path, lines)
    print(f"({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
