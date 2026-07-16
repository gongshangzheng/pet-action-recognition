"""Generic markdown-table CRUD helpers for upstream / downstream management data.

These helpers are **self-locating** (resolve the repo root from the script's
own path via ``parents[4]``), so the SAME script file works unchanged in both
upstream and downstream repos as long as it lives at
``.claude/skills/<management-skill>/scripts/``.

The markdown table editor is **schema-agnostic**: it auto-detects columns
from each section's header row, so it works on ``tasks.md`` (3 sections,
distinct columns), ``team/README.md`` (member list), ``milestones.md``, etc.
The backend parser keys cells by header name, so as long as we preserve the
header row and emit rows whose cell count matches the header, the parser is
happy.

Conventions:
- Line-based editing — blank lines, prose, and trailing sections are preserved.
- Immutable: every operation returns a NEW list of lines; nothing is mutated.
- Atomic writes (tmp + os.replace) — no half-written files.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

# .claude/skills/<skill>/scripts/X.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
MGMT_DIR = REPO_ROOT / "management"

TODAY = date.today().isoformat()


# --------------------------------------------------------------------------- #
# Path helpers                                                                #
# --------------------------------------------------------------------------- #
def tasks_md() -> Path:
    return MGMT_DIR / "docs" / "tasks.md"


def milestones_md() -> Path:
    return MGMT_DIR / "docs" / "milestones.md"


def team_readme() -> Path:
    return MGMT_DIR / "team" / "README.md"


def team_dir() -> Path:
    return MGMT_DIR / "team"


def meetings_dir() -> Path:
    return MGMT_DIR / "docs" / "meetings"


def meeting_path(iso_date: str) -> Path:
    return meetings_dir() / f"{iso_date}.md"


def daily_dir() -> Path:
    return MGMT_DIR / "daily"


def weekly_dir() -> Path:
    return MGMT_DIR / "weekly"


def monthly_dir() -> Path:
    return MGMT_DIR / "monthly"


def report_path(
    rtype: str,
    author: str,
    *,
    date: str | None = None,
    year: str | None = None,
    week: str | None = None,
    month: str | None = None,
) -> Path:
    """Resolve a report file path for daily / weekly / monthly.

    daily:   management/daily/{YYYY}/{MM}/{DD}-{author}.md     (--date YYYY-MM-DD)
    weekly:  management/weekly/{YYYY}/W{NN}-{author}.md         (--year --week)
    monthly: management/monthly/{YYYY}/{MM}-{author}.md         (--year --month)
    """
    if rtype == "daily":
        if not date:
            sys.exit("error: --date YYYY-MM-DD required for daily reports")
        y, m, d = date.split("-")
        return daily_dir() / y / m / f"{d}-{author}.md"
    if rtype == "weekly":
        y = year or sys.exit("error: --year required for weekly reports")
        w = (week or "").lstrip("Ww")
        if not w.isdigit():
            sys.exit("error: --week must be a number (e.g. 28 or W28)")
        return weekly_dir() / y / f"W{int(w):02d}-{author}.md"
    if rtype == "monthly":
        y = year or sys.exit("error: --year required for monthly reports")
        m = month or sys.exit("error: --month required for monthly reports")
        return monthly_dir() / y / f"{m}-{author}.md"
    sys.exit(f"error: unknown report type {rtype!r} (expected daily/weekly/monthly)")


def rel(path: Path) -> Path:
    """Return path relative to repo root (for friendly logs/errors)."""
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


# --------------------------------------------------------------------------- #
# File IO (atomic)                                                            #
# --------------------------------------------------------------------------- #
def read_lines(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"error: {rel(path)} not found")
    return path.read_text(encoding="utf-8").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    """Atomic write: tmp file in same dir + os.replace. Adds trailing newline."""
    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + "_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def read_text(path: Path) -> str:
    if not path.exists():
        sys.exit(f"error: {rel(path)} not found")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Markdown table line helpers                                                 #
# --------------------------------------------------------------------------- #
def is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def is_separator(line: str) -> bool:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return False
    inner = s.strip("|")
    return all(set(c) <= {"-", ":", " "} for c in inner.split("|")) and "-" in inner


def split_row(line: str) -> list[str]:
    """'| a | b |' -> ['a', 'b'] (stripped)."""
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def section_header_index(lines: list[str], section: str) -> int:
    """Index of the `## <section>` line. Exit if not found."""
    target = f"## {section}"
    for i, line in enumerate(lines):
        if line.strip() == target:
            return i
    sys.exit(f"error: section {section!r} not found in {rel(tasks_md())}")


def table_block_range(lines: list[str], header_idx: int) -> tuple[int, int]:
    """Range [start, end) of the contiguous `|`-block for a section.

    `start` = table header row; `end` = first non-table line after it.
    Returns (end, end) if the section has no table.
    """
    i = header_idx + 1
    while i < len(lines) and not is_table_line(lines[i]):
        i += 1
    start = i
    while i < len(lines) and is_table_line(lines[i]):
        i += 1
    return start, i


def row_lines_range(lines: list[str], header_idx: int) -> tuple[int, int]:
    """Range [start, end) of DATA rows (excluding header + separator)."""
    t_start, t_end = table_block_range(lines, header_idx)
    if t_start == t_end:
        return t_start, t_end
    data_start = t_start + 1  # skip header
    if data_start < t_end and is_separator(lines[data_start]):
        data_start += 1  # skip separator
    return data_start, t_end


def header_cols(lines: list[str], header_idx: int) -> list[str]:
    """Auto-detect column names from the section's table header row."""
    t_start, _ = table_block_range(lines, header_idx)
    if t_start >= len(lines) or not is_table_line(lines[t_start]):
        return []
    return split_row(lines[t_start])


# --------------------------------------------------------------------------- #
# Row operations (return NEW list of lines — immutable)                       #
# --------------------------------------------------------------------------- #
def find_row(lines: list[str], section: str, key: str) -> tuple[int, dict[str, str]]:
    """Find the data row whose FIRST cell == key. Returns (line_index, row_dict)."""
    cols = header_cols(lines, section_header_index(lines, section))
    return find_row_by_col(lines, section, cols[0], key)


def find_row_by_col(
    lines: list[str], section: str, col: str, value: str,
) -> tuple[int, dict[str, str]]:
    """Find the data row whose ``col`` cell == ``value``. Returns (idx, row_dict)."""
    header_idx = section_header_index(lines, section)
    cols = header_cols(lines, header_idx)
    if col not in cols:
        sys.exit(f"error: column {col!r} not in section {section!r} (cols: {cols})")
    data_start, data_end = row_lines_range(lines, header_idx)
    for i in range(data_start, data_end):
        line = lines[i]
        if not is_table_line(line) or is_separator(line):
            continue
        cells = split_row(line)
        idx = cols.index(col)
        if cells[idx] == value:
            return i, dict(zip(cols, cells))
    sys.exit(f"error: {value!r} not found in column {col!r} of {section!r} ({rel(tasks_md())})")


def list_rows(lines: list[str], section: str) -> list[dict[str, str]]:
    """All data rows in a section as dicts (keyed by header columns)."""
    header_idx = section_header_index(lines, section)
    cols = header_cols(lines, header_idx)
    data_start, data_end = row_lines_range(lines, header_idx)
    out: list[dict[str, str]] = []
    for i in range(data_start, data_end):
        line = lines[i]
        if not is_table_line(line) or is_separator(line):
            continue
        cells = split_row(line)
        out.append(dict(zip(cols, cells)))
    return out


def add_row(lines: list[str], section: str, values: dict[str, str]) -> list[str]:
    """Append a data row to ``section``. Columns auto-detected from the header."""
    header_idx = section_header_index(lines, section)
    cols = header_cols(lines, header_idx)
    if not cols:
        sys.exit(f"error: section {section!r} has no table header to derive columns from")
    if not values.get(cols[0]):
        sys.exit(f"error: {cols[0]!r} (first column) is required to add a row")
    cells = [values.get(c, "") for c in cols]
    _, data_end = row_lines_range(lines, header_idx)
    insert_at = data_end
    return lines[:insert_at] + [join_row(cells)] + lines[insert_at:]


def update_row(
    lines: list[str], section: str, key: str, updates: dict[str, str],
) -> list[str]:
    """Apply ``updates`` (keyed by column name) to the row whose first cell == key."""
    header_idx = section_header_index(lines, section)
    cols = header_cols(lines, header_idx)
    idx, row = find_row(lines, section, key)
    new_row = dict(row)
    for col, val in updates.items():
        if col not in cols:
            sys.exit(f"error: column {col!r} not in section {section!r} (cols: {cols})")
        new_row[col] = val
    cells = [new_row.get(c, "") for c in cols]
    return lines[:idx] + [join_row(cells)] + lines[idx + 1:]


def delete_row(lines: list[str], section: str, key: str) -> list[str]:
    """Remove the data row whose first cell == key."""
    idx, _ = find_row(lines, section, key)
    return lines[:idx] + lines[idx + 1:]


def update_row_by_col(
    lines: list[str], section: str, col: str, value: str, updates: dict[str, str],
) -> list[str]:
    """Apply ``updates`` to the row whose ``col`` cell == ``value``."""
    idx, row = find_row_by_col(lines, section, col, value)
    cols = header_cols(lines, section_header_index(lines, section))
    for c in updates:
        if c not in cols:
            sys.exit(f"error: column {c!r} not in section {section!r} (cols: {cols})")
    new_row = dict(row)
    new_row.update(updates)
    cells = [new_row.get(c, "") for c in cols]
    return lines[:idx] + [join_row(cells)] + lines[idx + 1:]


def delete_row_by_col(lines: list[str], section: str, col: str, value: str) -> list[str]:
    """Remove the data row whose ``col`` cell == ``value``."""
    idx, _ = find_row_by_col(lines, section, col, value)
    return lines[:idx] + lines[idx + 1:]


def move_row(
    lines: list[str],
    from_section: str,
    key: str,
    to_section: str,
    remap: dict[str, str] | None = None,
) -> list[str]:
    """Move a row between sections. ``remap`` = {target_column: value}; carries
    over columns that share a name between source and target when unset."""
    remap = remap or {}
    _, src_row = find_row(lines, from_section, key)
    target_cols = header_cols(lines, section_header_index(lines, to_section))
    values: dict[str, str] = {}
    for col in target_cols:
        if col in remap:
            values[col] = remap[col]
        elif col in src_row:
            values[col] = src_row[col]
        elif col == "完成日期":
            values[col] = remap.get("完成日期", TODAY)
        elif col == "产出":
            values[col] = remap.get("产出", src_row.get("备注", ""))
        else:
            values[col] = remap.get(col, "")
    without = delete_row(lines, from_section, key)
    return add_row(without, to_section, values)


# --------------------------------------------------------------------------- #
# Free-form markdown helpers (meetings / reports / member profiles)          #
# --------------------------------------------------------------------------- #
def find_header_line(lines: list[str], header: str) -> int:
    """Index of the line exactly equal to ``header`` (e.g. '## 基本信息'), else -1."""
    for i, line in enumerate(lines):
        if line.strip() == header:
            return i
    return -1


def section_end(lines: list[str], start_idx: int) -> int:
    """First index after ``start_idx`` that begins a new '## ' section, or len."""
    for j in range(start_idx + 1, len(lines)):
        if lines[j].lstrip().startswith("## "):
            return j
    return len(lines)


def replace_bullet_field(lines: list[str], label: str, value: str) -> list[str]:
    """Replace the value of a `- <label>：<value>` or `| <label> | <value> |` line.

    Used for meeting basic-info bullets (参会人：...) and member profile table
    rows (| 姓名 | ... |). Returns a new list; exits if the label is not found.
    """
    for i, line in enumerate(lines):
        s = line.strip()
        # bullet form: "- 参会人：张三"  (also match ':' ascii colon)
        if s.startswith("- ") and (label + "：") in s:
            new = f"- {label}：{value}"
            return lines[:i] + [new] + lines[i + 1:]
        if s.startswith("- ") and (label + ":") in s:
            new = f"- {label}:{value}"
            return lines[:i] + [new] + lines[i + 1:]
        # table cell form: "| 姓名 | 张三 |"
        if s.startswith("|") and s.endswith("|"):
            cells = split_row(line)
            if len(cells) >= 2 and cells[0] == label:
                cells[1] = value
                return lines[:i] + [join_row(cells)] + lines[i + 1:]
    sys.exit(f"error: field {label!r} not found in file")


def append_to_section(lines: list[str], header: str, bullets: list[str]) -> list[str]:
    """Append bullet lines to the END of a ``## <header>`` section's content.

    Trims trailing blank lines of the section, appends the bullets, then
    restores a single blank line before the next section. Exits if header
    is missing.
    """
    idx = find_header_line(lines, header)
    if idx < 0:
        sys.exit(f"error: section {header!r} not found")
    end = section_end(lines, idx)
    # walk back over trailing blank lines so we append right after last content
    insert_at = end
    while insert_at - 1 > idx and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    block = bullets + [""]
    return lines[:insert_at] + block + lines[insert_at:]


# --------------------------------------------------------------------------- #
# JSON task-tree IO (single source: projects/{slug}/tasks.json)              #
# --------------------------------------------------------------------------- #
# 任务数据的唯一来源是 per-project tasks.json（层级树，与项目树页同源）。
# tasks.md 已废弃删除；看板是其派生视图。

import json
import re as _re

_PROJECTS_DIR = MGMT_DIR / "docs" / "projects"
_SLUG_RE = _re.compile(r"^[A-Za-z0-9_-]+$")

# canonical task statuses + 看板桶映射
TASK_STATUSES = ("completed", "active", "planned", "paused", "blocked")
STATUS_BUCKET = {
    "completed": "completed",
    "active": "in_progress",
    "planned": "pending",
    "paused": "pending",
    "blocked": "pending",
}


def _validate_slug(slug: str) -> str:
    if not slug or not _SLUG_RE.match(slug):
        sys.exit(f"error: invalid project slug {slug!r} (allowed: letters, digits, _, -)")
    return slug


def projects_dir() -> Path:
    return _PROJECTS_DIR


def tasks_json_path(slug: str) -> Path:
    """per-project tasks.json 路径。slug 非法则报错。"""
    _validate_slug(slug)
    return _PROJECTS_DIR / slug / "tasks.json"


def list_project_slugs() -> list[str]:
    """列出所有有 tasks.json 的项目 slug。"""
    if not _PROJECTS_DIR.is_dir():
        return []
    out = []
    for slug in os.listdir(_PROJECTS_DIR):
        if _SLUG_RE.match(slug) and tasks_json_path(slug).is_file():
            out.append(slug)
    return sorted(out)


def read_tasks(slug: str) -> dict:
    """读 projects/{slug}/tasks.json，返回 {project, tasks: [...]} 树。"""
    path = tasks_json_path(slug)
    if not path.is_file():
        sys.exit(f"error: {rel(path)} not found (项目 {slug!r} 无 tasks.json)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"error: {rel(path)} invalid JSON: {e}")
    if not isinstance(data, dict) or "tasks" not in data:
        sys.exit(f"error: {rel(path)} 顶层需为 {{'project':..., 'tasks':[...]}}")
    return data


def write_tasks(slug: str, tree: dict) -> None:
    """原子写 projects/{slug}/tasks.json（tmp + os.replace，缩进 2 空格）。"""
    path = tasks_json_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(tree, ensure_ascii=False, indent=2) + "\n"
    write_text(path, text)


def find_task_by_id(tasks: list, task_id: str):
    """递归查找 id == task_id 的节点。

    返回 (parent_list, index, task) 以便就地增删改；找不到返回 (None, -1, None)。
    """
    for i, t in enumerate(tasks):
        if t.get("id") == task_id:
            return tasks, i, t
        children = t.get("children") or []
        if children:
            pl, idx, found = find_task_by_id(children, task_id)
            if found is not None:
                return pl, idx, found
    return None, -1, None


def flatten_tasks(tasks: list, acc=None) -> list[dict]:
    """递归展平任务树为看板卡列表（每个节点一张卡，含父子）。"""
    if acc is None:
        acc = []
    for t in tasks or []:
        acc.append({
            "id": t.get("id", ""),
            "name": t.get("title", ""),
            "owner": t.get("assignee", ""),
            "start_date": t.get("startDate", ""),
            "end_date": t.get("endDate", ""),
            "status": t.get("status", "planned"),
            "note": t.get("description", ""),
            "priority": t.get("priority"),
        })
        if t.get("children"):
            flatten_tasks(t["children"], acc)
    return acc


def next_task_id(tasks: list, parent_id: str | None) -> str:
    """生成下一个不重复的 id。

    无 parent：t{N}（N = 现有根级 tN 的最大 N + 1）。
    有 parent：{parent}-{N}（N = 该 parent 现有 children 的最大尾号 + 1）。
    """
    existing = _collect_ids(tasks)

    def used(i: str) -> bool:
        return i in existing

    if not parent_id:
        n = 1
        while used(f"t{n}"):
            n += 1
        return f"t{n}"

    # 在 parent 下追加 child
    parent = find_task_by_id(tasks, parent_id)[2]
    if parent is None:
        sys.exit(f"error: parent task {parent_id!r} not found")
    children = parent.get("children") or []
    child_nums = []
    for c in children:
        cid = c.get("id", "")
        m = _re.match(r"^-?(\d+)$", cid.rsplit("-", 1)[-1] if "-" in cid else cid)
        if m:
            child_nums.append(int(m.group(1)))
    n = (max(child_nums) + 1) if child_nums else 1
    candidate = f"{parent_id}-{n}"
    while used(candidate):
        n += 1
        candidate = f"{parent_id}-{n}"
    return candidate


def _collect_ids(tasks: list, acc=None) -> set[str]:
    if acc is None:
        acc = set()
    for t in tasks or []:
        if t.get("id"):
            acc.add(t["id"])
        if t.get("children"):
            _collect_ids(t["children"], acc)
    return acc


