#!/usr/bin/env python3
"""Add a task node to management/docs/projects/{slug}/tasks.json.

Operates on the hierarchical task tree (single source of truth, shared with
the project-tree page). New node is appended to the root list, or to a
parent's `children` when --parent is given. id auto-generated (tN / parent-N).

Self-locating: run from anywhere; resolves the repo root from its own path.
Mirrors the same file in ~/infraredComp (identical tasks.json schema).

Usage:
    # root task
    python3 add_task.py --slug projflow --title "轮廓提取优化" --status active \\
        --assignee 张三 --start 2026-07-11 --end 2026-07-18 \\
        --description "sobel 降噪" --note-path notes/contour.md
    # child under t2
    python3 add_task.py --slug projflow --parent t2 --title "AV1 baseline" \\
        --status planned --priority P1
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io
import task_schema


def build_node(args, new_id: str) -> dict:
    node = {
        "id": new_id,
        "title": args.title,
        "status": task_schema.resolve_status(args.status),
    }
    if args.assignee:
        node["assignee"] = args.assignee
    if args.start:
        node["startDate"] = args.start
    if args.end:
        node["endDate"] = args.end
    if args.description:
        node["description"] = args.description
    if args.note_path:
        node["notePath"] = args.note_path
    if args.priority:
        node["priority"] = args.priority
    if args.hidden:
        node["hidden"] = True
    node["children"] = []
    return node


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="project slug (projects/{slug}/tasks.json)")
    ap.add_argument("--title", required=True, help="task title")
    ap.add_argument("--status", default="planned", help="completed/active/planned/paused/blocked (default: planned)")
    ap.add_argument("--assignee", default="", help="负责人")
    ap.add_argument("--start", default="", help="startDate (YYYY-MM-DD)")
    ap.add_argument("--end", default="", help="endDate (YYYY-MM-DD)")
    ap.add_argument("--description", default="", help="任务描述")
    ap.add_argument("--note-path", default="", help="相对项目目录的笔记 markdown 路径")
    ap.add_argument("--priority", default="", help="优先级 (e.g. P1)")
    ap.add_argument("--hidden", action="store_true", help="标记为不展示（项目树默认隐藏，可通过眼睛图标切换显示）")
    ap.add_argument("--parent", default="", help="父任务 id；省略则加到根级")
    args = ap.parse_args()

    tree = mgmt_io.read_tasks(args.slug)
    tasks = tree.setdefault("tasks", [])
    new_id = mgmt_io.next_task_id(tasks, args.parent or None)
    node = build_node(args, new_id)

    if args.parent:
        parent = mgmt_io.find_task_by_id(tasks, args.parent)[2]
        if parent is None:
            sys.exit(f"error: parent task {args.parent!r} not found in {args.slug!r}")
        parent.setdefault("children", []).append(node)
        location = f"under {args.parent}"
    else:
        tasks.append(node)
        location = "at root"

    mgmt_io.write_tasks(args.slug, tree)
    path = mgmt_io.tasks_json_path(args.slug)
    print(f"✓ added task {new_id!r} ({node['status']}) {location}  ({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
