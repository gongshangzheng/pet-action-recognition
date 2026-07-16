#!/usr/bin/env python3
"""Delete a report file (daily / weekly / monthly).

Usage:
    python3 delete_report.py --type daily   --author zhangsan --date 2026-07-11
    python3 delete_report.py --type weekly  --author zhangsan --year 2026 --week 28
    python3 delete_report.py --type monthly --author zhangsan --year 2026 --month 07
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


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
    if not path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} not found")
    path.unlink()
    print(f"✓ deleted {args.type} report {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
