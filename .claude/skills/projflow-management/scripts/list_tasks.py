#!/usr/bin/env python3
"""List tasks in management/docs/projects/{slug}/tasks.json (tree or flat).

Single source of truth is the per-project tasks.json (hierarchical tree, shared
with the project-tree page). The kanban board is a derived flatten-view.

Self-locating: run from anywhere; resolves the repo root from its own path.
Mirrors the same file in ~/infraredComp (identical tasks.json schema).

Usage:
    python3 list_tasks.py --slug projflow                 # tree view
    python3 list_tasks.py --slug projflow --flat          # flat (kanban buckets)
    python3 list_tasks.py --slug projflow --status active # filter by status
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io
import task_schema


def print_tree(tasks: list, depth: int = 0) -> int:
    prefix = "  " * depth
    total = 0
    for t in tasks:
        total += 1
        children = t.get("children") or []
        bullet = "▾" if children else "•"
        line = f"{prefix}{bullet} [{t.get('id','')}] {t.get('title','')}  ({t.get('status','')})"
        assignee = t.get("assignee")
        if assignee:
            line += f"  @{assignee}"
        dates = t.get("startDate") or t.get("endDate")
        if dates:
            line += f"  {t.get('startDate','')}~{t.get('endDate','')}"
        print(line)
        if children:
            total += print_tree(children, depth + 1)
    return total


def print_flat(tasks: list, status_filter: str | None) -> int:
    cards = mgmt_io.flatten_tasks(tasks)
    if status_filter:
        cards = [c for c in cards if c["status"] == status_filter]
    buckets = {"in_progress": [], "pending": [], "completed": []}
    for c in cards:
        buckets[mgmt_io.STATUS_BUCKET.get(c["status"], "pending")].append(c)
    total = 0
    for bucket, label in (("pending", "待开始"), ("in_progress", "进行中"), ("completed", "已完成")):
        rows = buckets[bucket]
        print(f"\n## {label}  ({len(rows)})")
        if not rows:
            print("  (empty)")
        for c in rows:
            extra = []
            if c["owner"]:
                extra.append(f"@{c['owner']}")
            if c["end_date"]:
                extra.append(c["end_date"])
            if c["note"]:
                extra.append(c["note"])
            tail = "  " + " ".join(extra) if extra else ""
            print(f"  [{c['id']}] {c['name']}  ({c['status']}){tail}")
        total += len(rows)
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="project slug (projects/{slug}/tasks.json)")
    ap.add_argument("--flat", action="store_true", help="flat kanban-bucket view (default: tree)")
    ap.add_argument("--status", default=None, help="filter by status (completed/active/planned/paused/blocked)")
    args = ap.parse_args()

    if args.status:
        args.status = task_schema.resolve_status(args.status)

    tree = mgmt_io.read_tasks(args.slug)
    tasks = tree.get("tasks", [])
    if args.flat or args.status:
        total = print_flat(tasks, args.status)
    else:
        total = print_tree(tasks)
    print(f"\n{total} task(s) total  ({mgmt_io.rel(mgmt_io.tasks_json_path(args.slug))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
