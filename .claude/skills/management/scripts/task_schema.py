"""Task schema constants for the per-project tasks.json tree.

Upstream and downstream repos use an IDENTICAL tasks.json schema (single source of
truth for both the project tree and the kanban board). The kanban is a derived
view that flattens the tree into three buckets by status — see
``server/parsers/tasks_parser.py`` and ``mgmt_io.STATUS_BUCKET``.

Task node shape:
    {
      "id": "t1-1",                  # unique within the project
      "title": "...",
      "status": <STATUS>,            # one of TASK_STATUSES below
      "startDate": "2026-07-08",     # ISO date or null
      "endDate": "2026-07-10",
      "assignee": "张三",
      "description": "...",
      "notePath": "notes/01.md",     # optional, relative to project dir
      "priority": "P1",              # optional
      "hidden": true,                # optional, hide in project tree
      "progress": [                  # optional, newest first
        { "date": "2026-07-16", "note": "完成了 X" }
      ],
      "children": [ ... recursive ... ]
    }

Kanban bucket mapping (status -> bucket):
    completed -> completed
    active    -> in_progress
    planned / paused / blocked -> pending
"""

from __future__ import annotations

import sys

# canonical task statuses (stored on each node's `status` field)
TASK_STATUSES = ("completed", "active", "planned", "paused", "blocked")

# status -> 看板桶（与 server/parsers/tasks_parser._BUCKET、mgmt_io.STATUS_BUCKET 一致）
STATUS_BUCKET = {
    "completed": "completed",
    "active": "in_progress",
    "planned": "pending",
    "paused": "pending",
    "blocked": "pending",
}

# task node fields the CRUD scripts may set/update (excluding id/children)
TASK_FIELDS = ("title", "status", "startDate", "endDate", "assignee",
               "description", "notePath", "priority", "progress")


def resolve_status(s: str) -> str:
    """Validate / normalize a status arg against TASK_STATUSES.

    Accepts canonical names and a few aliases. Exits on unknown values.
    """
    aliases = {
        "done": "completed",
        "in_progress": "active",
        "ongoing": "active",
        "todo": "planned",
        "pending": "planned",
    }
    key = s.strip().lower()
    if key in TASK_STATUSES:
        return key
    if key in aliases:
        return aliases[key]
    sys.exit(
        f"error: unknown status {s!r}. Expected one of {TASK_STATUSES} "
        f"(or aliases: done/in_progress/ongoing/todo/pending)."
    )


def bucket_for(status: str) -> str:
    """Map a canonical status to its kanban bucket."""
    return STATUS_BUCKET.get(status, "pending")
