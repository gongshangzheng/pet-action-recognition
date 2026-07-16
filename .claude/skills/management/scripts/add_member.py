#!/usr/bin/env python3
"""Add a team member to management/team/.

Two steps:
1. Append a row to the 成员列表 table in management/team/README.md
   (and drop the "暂无" placeholder row when the first real member is added).
2. Create the profile management/team/{id}.md from a template.

Self-locating; argparse; identical file used in upstream and downstream repos.

Usage:
    python3 add_member.py --name 张三 --id zhangsan --role 算法工程师 \\
        --join-date 2026-01-15 --research "红外视频压缩" \\
        --tech "Python,PyTorch,ffmpeg" --modules "评测,论文"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io

MEMBER_SECTION = "成员列表"

PROFILE_TEMPLATE = """# {name}

## 基本信息

| 字段 | 内容 |
|------|------|
| 姓名 | {name} |
| 英文标识 | {id} |
| 角色 | {role} |
| 入职日期 | {join_date} |
| 研究方向 | {research} |

## 技术栈

{tech_list}

## 负责模块

{module_list}

## 备注

{note}
"""


def ensure_readme(readme: Path) -> None:
    if readme.exists():
        return
    content = (
        "# 团队成员\n\n"
        "本目录存放团队所有成员的档案文件。\n\n"
        "## 成员列表\n\n"
        "| 姓名 | 英文标识 | 角色 | 入职日期 |\n"
        "|------|----------|------|----------|\n"
        "| 暂无 | — | — | — |\n\n"
        "## 新增成员\n\n"
        "新成员入职时，请复制模板创建新的档案文件，命名格式为 `姓名.md`。\n"
    )
    mgmt_io.write_text(readme, content)


def add_to_readme(args) -> None:
    readme = mgmt_io.team_readme()
    ensure_readme(readme)
    lines = mgmt_io.read_lines(readme)
    existing = mgmt_io.list_rows(lines, MEMBER_SECTION)
    if any(r.get("英文标识") == args.id for r in existing):
        sys.exit(f"error: member {args.id!r} already exists in {mgmt_io.rel(readme)}")
    # drop the 暂无 placeholder when adding a real member
    if any(r.get("姓名") == "暂无" for r in existing):
        lines = mgmt_io.delete_row_by_col(lines, MEMBER_SECTION, "姓名", "暂无")
    values = {
        "姓名": args.name,
        "英文标识": args.id,
        "角色": args.role,
        "入职日期": args.join_date,
    }
    lines = mgmt_io.add_row(lines, MEMBER_SECTION, values)
    mgmt_io.write_lines(readme, lines)
    print(f"✓ added member {args.name!r} ({args.id}) to list  ({mgmt_io.rel(readme)})")


def create_profile(args) -> None:
    profile = mgmt_io.team_dir() / f"{args.id}.md"
    if profile.exists():
        print(f"! profile {mgmt_io.rel(profile)} already exists, skipped", file=sys.stderr)
        return
    tech_list = "\n".join(f"- {t.strip()}" for t in args.tech.split(",") if t.strip()) or "- "
    module_list = "\n".join(f"- {m.strip()}" for m in args.modules.split(",") if m.strip()) or "- 待分配"
    text = PROFILE_TEMPLATE.format(
        name=args.name, id=args.id, role=args.role, join_date=args.join_date,
        research=args.research, tech_list=tech_list, module_list=module_list,
        note=args.note or "无",
    )
    mgmt_io.write_text(profile, text)
    print(f"✓ created profile {mgmt_io.rel(profile)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--id", required=True, help="english identifier (profile filename stem)")
    ap.add_argument("--role", required=True)
    ap.add_argument("--join-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--research", default="", help="研究方向")
    ap.add_argument("--tech", default="", help="comma-separated tech stack")
    ap.add_argument("--modules", default="", help="comma-separated responsible modules")
    ap.add_argument("--note", default="", help="备注")
    args = ap.parse_args()

    add_to_readme(args)
    create_profile(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
