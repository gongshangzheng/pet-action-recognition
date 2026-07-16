"""任务看板解析器 — 从 per-project tasks.json 派生看板。

任务数据的**唯一来源**是 `management/docs/projects/{slug}/tasks.json`（层级任务树，
与项目树页同源）。看板不再有独立的 tasks.md；本解析器读取项目任务树，递归展平
所有节点，按 status 映射进三个看板桶：

    completed → completed
    active    → in_progress
    planned / paused / blocked → pending
"""
from server.parsers.projects_parser import get_project_tasks

# status → 看板桶
_BUCKET = {
    'completed': 'completed',
    'active': 'in_progress',
    'planned': 'pending',
    'paused': 'pending',
    'blocked': 'pending',
}


def parse_tasks(slug=None):
    """解析项目任务树，返回三个分组：in_progress, pending, completed。

    参数:
        slug: 项目 slug。None 时取首个项目；仍无则返回空三桶。

    返回: {in_progress: [...], pending: [...], completed: [...]}，
    每张卡 = {id, name, owner, start_date, end_date, status, note, priority?}。
    """
    slug = _resolve_slug(slug)
    if not slug:
        return _copy_empty()

    tree = get_project_tasks(slug)
    if not tree:
        return _copy_empty()

    result = {'in_progress': [], 'pending': [], 'completed': []}
    for card in _flatten(tree.get('tasks', [])):
        bucket = _BUCKET.get(card['status'], 'pending')
        result[bucket].append(card)
    return result


# ── 内部工具 ────────────────────────────────────────────────────

def _resolve_slug(slug):
    """slug 为空时回退到首个项目。"""
    if slug:
        return slug
    # 延迟导入避免循环依赖
    from server.parsers.projects_parser import list_projects
    projects = list_projects()
    return projects[0]['slug'] if projects else None


def _copy_empty():
    return {'in_progress': [], 'pending': [], 'completed': []}


def _flatten(tasks, acc=None):
    """递归展平任务树为看板卡列表（保留每个节点，含父任务）。"""
    if acc is None:
        acc = []
    for t in tasks or []:
        acc.append({
            'id': t.get('id', ''),
            'name': t.get('title', ''),
            'owner': t.get('assignee', ''),
            'start_date': t.get('startDate', ''),
            'end_date': t.get('endDate', ''),
            'status': t.get('status', 'planned'),
            'note': t.get('description', ''),
            'priority': t.get('priority'),
        })
        if t.get('children'):
            _flatten(t['children'], acc)
    return acc
