#!/usr/bin/env python3
"""Delete a meeting minutes file management/docs/meetings/{date}.md.

Usage:
    python3 delete_meeting.py --date 2026-07-11
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="meeting date YYYY-MM-DD")
    args = ap.parse_args()

    path = mgmt_io.meeting_path(args.date)
    if not path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} not found")
    path.unlink()
    print(f"✓ deleted meeting {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
