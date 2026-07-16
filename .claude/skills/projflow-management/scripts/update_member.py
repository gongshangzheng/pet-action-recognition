#!/usr/bin/env python3
"""Update a team member's info in management/team/.

Touches TWO places:
1. The member-list table in management/team/README.md (match by 英文标识 column):
   updates 姓名 / 英文标识 / 角色 / 入职日期.
2. The basic-info table inside management/team/{id}.md: updates
   姓名 / 英文标识 / 角色 / 入职日期 / 研究方向 (table-cell rows).

--new-id renames the profile file {old}.md -> {new}.md.

Usage:
    python3 update_member.py --id zhangsan --role "高级算法工程师" --join-date 2026-01-15
    python3 update_member.py --id zhangsan --name 张三丰 --new-id zhangsanfeng
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

MEMBER_SECTION = "成员列表"


def update_readme_row(lines, a) -> list[str]:
    updates: dict[str, str] = {}
    if a.name is not None:
        updates["姓名"] = a.name
    if a.new_id is not None:
        updates["英文标识"] = a.new_id
    if a.role is not None:
        updates["角色"] = a.role
    if a.join_date is not None:
        updates["入职日期"] = a.join_date
    if not updates:
        return lines
    return mgmt_io.update_row_by_col(lines, MEMBER_SECTION, "英文标识", a.id, updates)


def update_profile_fields(profile_path, a) -> str:
    text = mgmt_io.read_text(profile_path)
    lines = text.splitlines()
    field_map = {
        "姓名": a.name,
        "英文标识": a.new_id,
        "角色": a.role,
        "入职日期": a.join_date,
        "研究方向": a.research,
    }
    for field, val in field_map.items():
        if val is not None:
            lines = mgmt_io.replace_bullet_field(lines, field, val)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="current 英文标识 (lookup key)")
    ap.add_argument("--name", default=None, help="update 姓名")
    ap.add_argument("--role", default=None, help="update 角色")
    ap.add_argument("--join-date", default=None, help="update 入职日期 (YYYY-MM-DD)")
    ap.add_argument("--research", default=None, help="update 研究方向 (profile only)")
    ap.add_argument("--new-id", default=None, help="rename 英文标识 (also renames profile file)")
    args = ap.parse_args()

    # 1) README member-list table
    readme = mgmt_io.team_readme()
    lines = mgmt_io.read_lines(readme)
    new_lines = update_readme_row(lines, args)
    mgmt_io.write_lines(readme, new_lines)
    print(f"✓ updated member list row (id={args.id})  ({mgmt_io.rel(readme)})")

    # 2) profile file (rename if --new-id)
    old_profile = mgmt_io.team_dir() / f"{args.id}.md"
    target_id = args.new_id or args.id
    new_profile = mgmt_io.team_dir() / f"{target_id}.md"
    if old_profile.exists():
        text = update_profile_fields(old_profile, args)
        mgmt_io.write_text(new_profile, text)
        if args.new_id and old_profile != new_profile:
            old_profile.unlink()
            print(f"✓ renamed profile {args.id}.md -> {target_id}.md")
        else:
            print(f"✓ updated profile {target_id}.md  ({mgmt_io.rel(new_profile)})")
    else:
        print(f"! profile {mgmt_io.rel(old_profile)} not found (only README row updated)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
