"""项目树解析器 — 解析 management/docs/projects/{slug}/ 下的项目数据"""
import json
import os
import re

import yaml

from server.config import MANAGEMENT_DIR
from server.utils.file_utils import read_file, safe_resolve

# 项目目录：management/docs/projects/
PROJECTS_DIR = os.path.join(MANAGEMENT_DIR, 'docs', 'projects')

# slug 只允许字母、数字、下划线、连字符
_SLUG_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def _is_valid_slug(slug):
    return isinstance(slug, str) and bool(_SLUG_RE.match(slug))


def _project_file_path(slug, *parts):
    """生成并校验项目目录内的安全路径；越界或非法 slug 返回 None。"""
    if not _is_valid_slug(slug):
        return None
    return safe_resolve(PROJECTS_DIR, slug, *parts)


def list_projects():
    """列出所有项目，按开始日期倒序。

    每个项目目录下需有 README.md（含 YAML frontmatter）。
    返回 [{slug, title, status, startDate, endDate, tags, participants}]。
    """
    if not os.path.isdir(PROJECTS_DIR):
        return []

    projects = []
    for slug in os.listdir(PROJECTS_DIR):
        project_base = _project_file_path(slug)
        if not project_base or not os.path.isdir(project_base):
            continue

        readme_path = os.path.join(project_base, 'README.md')
        if not os.path.isfile(readme_path):
            continue

        meta, _ = _parse_readme(read_file(readme_path))
        meta['slug'] = slug
        projects.append(meta)

    projects.sort(key=lambda p: p.get('startDate') or '', reverse=True)
    return projects


def get_project(slug):
    """获取单个项目元信息 + README 正文。"""
    readme_path = _project_file_path(slug, 'README.md')
    if not readme_path or not os.path.isfile(readme_path):
        return None

    meta, body = _parse_readme(read_file(readme_path))
    meta['slug'] = slug
    meta['body'] = body
    return meta


def get_project_tasks(slug):
    """读取项目任务树 tasks.json，并执行级联完成计算。"""
    tasks_path = _project_file_path(slug, 'tasks.json')
    if not tasks_path or not os.path.isfile(tasks_path):
        return None

    content = read_file(tasks_path)
    try:
        tree = json.loads(content) if content else None
    except json.JSONDecodeError:
        return None

    if not tree:
        return None

    tree['tasks'] = _cascade_status(tree.get('tasks', []))
    return tree


def get_task_note(slug, note_path):
    """读取项目下的任务笔记 markdown（notePath 相对项目目录）。"""
    if not isinstance(note_path, str):
        return None

    # 禁止绝对路径，并清除前导 /
    safe_note_path = note_path.lstrip('/')
    if not safe_note_path or safe_note_path.startswith('/'):
        return None

    full = _project_file_path(slug, safe_note_path)
    if not full or not os.path.isfile(full):
        return None

    return read_file(full)


def count_tasks(tasks):
    """递归统计任务总数与已完成数。"""
    total = 0
    completed = 0
    for t in tasks:
        total += 1
        if t.get('status') == 'completed':
            completed += 1
        children = t.get('children') or []
        if children:
            sub = count_tasks(children)
            total += sub['total']
            completed += sub['completed']
    return {'total': total, 'completed': completed}


# ── 内部工具 ────────────────────────────────────────────────────

def _parse_readme(text):
    """解析 README：YAML frontmatter + markdown 正文。"""
    meta = {
        'title': '',
        'status': 'planned',
        'startDate': None,
        'endDate': None,
        'tags': [],
        'participants': [],
    }
    body = text or ''

    match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.DOTALL)
    if match:
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            data = {}
        body = match.group(2)

        meta['title'] = str(data.get('title', '') or '')
        meta['status'] = str(data.get('status', 'planned') or 'planned')
        meta['startDate'] = data.get('startDate') or data.get('start_date')
        meta['endDate'] = data.get('endDate') or data.get('end_date')
        meta['tags'] = list(data.get('tags') or [])
        meta['participants'] = list(data.get('participants') or [])
    else:
        # 无 frontmatter，用首个 # 标题作为 title
        title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if title_match:
            meta['title'] = title_match.group(1).strip()

    return meta, body.strip()


def _cascade_status(tasks):
    """级联完成：所有子任务完成则父任务标记完成。"""
    result = []
    for t in tasks:
        children = t.get('children') or []
        if children:
            children = _cascade_status(children)
            t = {**t, 'children': children}
            if all(c.get('status') == 'completed' for c in children):
                t['status'] = 'completed'
        result.append(t)
    return result
