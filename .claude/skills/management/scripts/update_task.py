#!/usr/bin/env python3
"""Update a task node in management/docs/projects/{slug}/tasks.json.

Only fields passed on the CLI are changed; omitted fields keep their current
value. ``--status`` is the kanban "move between buckets" lever (status drives
which bucket a task appears in — completed/active/planned/paused/blocked).

Self-locating: run from anywhere; resolves the repo root from its own path.
Mirrors the same file in ~/infraredComp (identical tasks.json schema).

Usage:
    # change status / assignee
    python3 update_task.py --slug myproject --id t2-3 --status active --assignee 李四
    # rename + dates
    python3 update_task.py --slug myproject --id t2-3 --title "轮廓提取 v2" --end 2026-07-20
    # mark done
    python3 update_task.py --slug myproject --id t2-3 --status completed
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io
import task_schema

# CLI flag -> task node field; --status is normalized via resolve_status
FLAG_FIELD = {
    "title": "title",
    "assignee": "assignee",
    "start": "startDate",
    "end": "endDate",
    "description": "description",
    "note_path": "notePath",
    "priority": "priority",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="project slug")
    ap.add_argument("--id", required=True, help="task id (exact match)")
    ap.add_argument("--status", default=None, help="completed/active/planned/paused/blocked")
    ap.add_argument("--title", default=None)
    ap.add_argument("--assignee", default=None)
    ap.add_argument("--start", default=None, help="startDate (YYYY-MM-DD)")
    ap.add_argument("--end", default=None, help="endDate (YYYY-MM-DD)")
    ap.add_argument("--description", default=None)
    ap.add_argument("--note-path", default=None, help="相对项目目录的笔记 markdown 路径")
    ap.add_argument("--priority", default=None)
    ap.add_argument("--hidden", action="store_true", default=None,
                    help="标记为不展示（项目树默认隐藏）")
    ap.add_argument("--no-hidden", dest="hidden", action="store_false",
                    help="取消不展示标记")
    args = ap.parse_args()

    tree = mgmt_io.read_tasks(args.slug)
    tasks = tree.get("tasks", [])
    parent_list, idx, task = mgmt_io.find_task_by_id(tasks, args.id)
    if task is None:
        sys.exit(f"error: task {args.id!r} not found in project {args.slug!r}")

    updates = {}
    if args.status is not None:
        updates["status"] = task_schema.resolve_status(args.status)
    for flag, field in FLAG_FIELD.items():
        val = getattr(args, flag)
        if val is not None:
            updates[field] = val
    if args.hidden is True:
        updates["hidden"] = True

    if not updates and args.hidden is not False:
        print("no updates given; nothing to do.", file=sys.stderr)
        return 1

    # immutable: replace the node in its parent list
    new_task = {**task, **updates}
    removed_keys = []
    if args.hidden is False and "hidden" in task:
        new_task.pop("hidden", None)
        removed_keys.append("hidden")
    parent_list[idx] = new_task
    mgmt_io.write_tasks(args.slug, tree)
    path = mgmt_io.tasks_json_path(args.slug)
    changed = sorted(set(list(updates.keys()) + removed_keys))
    print(f"✓ updated task {args.id!r}: {', '.join(changed)}  ({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
