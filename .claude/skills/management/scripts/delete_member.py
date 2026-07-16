#!/usr/bin/env python3
"""Delete a team member from management/team/.

Removes the row in the member-list table (match by 英文标识) and deletes the
profile file management/team/{id}.md, unless --keep-profile is given.

Usage:
    python3 delete_member.py --id zhangsan
    python3 delete_member.py --id zhangsan --keep-profile
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

MEMBER_SECTION = "成员列表"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="英文标识 of the member to delete")
    ap.add_argument("--keep-profile", action="store_true", help="keep the {id}.md profile file")
    args = ap.parse_args()

    readme = mgmt_io.team_readme()
    lines = mgmt_io.read_lines(readme)
    new_lines = mgmt_io.delete_row_by_col(lines, MEMBER_SECTION, "英文标识", args.id)
    mgmt_io.write_lines(readme, new_lines)
    print(f"✓ removed member {args.id!r} from list  ({mgmt_io.rel(readme)})")

    profile = mgmt_io.team_dir() / f"{args.id}.md"
    if profile.exists() and not args.keep_profile:
        profile.unlink()
        print(f"✓ deleted profile {mgmt_io.rel(profile)}")
    elif args.keep_profile and profile.exists():
        print(f"! kept profile {mgmt_io.rel(profile)} (--keep-profile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
