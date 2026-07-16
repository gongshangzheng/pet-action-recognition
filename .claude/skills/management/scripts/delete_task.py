#!/usr/bin/env python3
"""Delete a task node from management/docs/projects/{slug}/tasks.json.

Recursively locates the node by id and removes it (including its children).

Self-locating: run from anywhere; resolves the repo root from its own path.
Mirrors the same file in ~/infraredComp (identical tasks.json schema).

Usage:
    python3 delete_task.py --slug myproject --id t2-3
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="project slug")
    ap.add_argument("--id", required=True, help="task id (exact match)")
    args = ap.parse_args()

    tree = mgmt_io.read_tasks(args.slug)
    tasks = tree.get("tasks", [])
    parent_list, idx, task = mgmt_io.find_task_by_id(tasks, args.id)
    if task is None:
        sys.exit(f"error: task {args.id!r} not found in project {args.slug!r}")

    title = task.get("title", "")
    del parent_list[idx]
    mgmt_io.write_tasks(args.slug, tree)
    path = mgmt_io.tasks_json_path(args.slug)
    print(f"✓ deleted task {args.id!r} ({title!r})  ({mgmt_io.rel(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
