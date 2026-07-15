"""项目管理路由"""
import os
import re
from fastapi import APIRouter, HTTPException
from server.config import MANAGEMENT_DIR
from server.utils.file_utils import read_file, safe_resolve, scan_directory
from server.parsers.team_parser import parse_team_list, parse_member_profile
from server.parsers.report_parser import get_report_list, get_report_detail
from server.parsers.tasks_parser import parse_tasks
from server.parsers.milestones_parser import parse_milestones
from server.parsers.projects_parser import (
    list_projects, get_project, get_project_tasks, get_task_note,
)

router = APIRouter(prefix="/api/management", tags=["management"])

# 日期/作者参数校验（防止路径遍历与非法文件名）
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_YEAR_RE = re.compile(r'^\d{4}$')
_MONTH_RE = re.compile(r'^(0[1-9]|1[0-2])$')
_DAY_RE = re.compile(r'^(0[1-9]|[12]\d|3[01])$')
_WEEK_RE = re.compile(r'^[1-5]?\d$')
_FILENAME_PART_RE = re.compile(r'^[^/\\\x00-\x1f\x7f]+$')


def _safe_report_path(base_dir, *parts):
    """安全拼接报告路径，确保位于 base_dir 内。"""
    filepath = safe_resolve(base_dir, *parts)
    if not filepath or not os.path.exists(filepath):
        return None
    return filepath


@router.get("/team")
async def get_team():
    """获取团队成员列表"""
    readme = read_file(os.path.join(MANAGEMENT_DIR, 'team', 'README.md'))
    return parse_team_list(readme)


@router.get("/team/{member_id}")
async def get_team_member(member_id: str):
    """获取成员档案详情"""
    team_dir = os.path.join(MANAGEMENT_DIR, 'team')
    # 遍历 .md 文件，找到英文标识匹配的成员
    for f in os.listdir(team_dir):
        if f.endswith('.md') and f != 'README.md':
            content = read_file(os.path.join(team_dir, f))
            if content:
                profile = parse_member_profile(content)
                if profile and profile['id'] == member_id:
                    return profile
    return {"detail": "Member not found"}, 404


@router.get("/daily")
async def get_daily_list():
    """获取日报列表"""
    return get_report_list('daily')


@router.get("/daily/{date}/{author}")
async def get_daily_detail(date: str, author: str):
    """获取指定日报内容"""
    # 从 date 解析年月日
    parts = date.split('-')
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid date")
    year, month, day = parts
    if not (_YEAR_RE.match(year) and _MONTH_RE.match(month) and _DAY_RE.match(day)):
        raise HTTPException(status_code=400, detail="Invalid date")
    if not _FILENAME_PART_RE.match(author):
        raise HTTPException(status_code=400, detail="Invalid author")

    # 尝试 YYYY/MM/DD-姓名.md
    filepath = _safe_report_path(
        os.path.join(MANAGEMENT_DIR, 'daily', year, month),
        f"{day}-{author}.md",
    )
    if filepath:
        result = get_report_detail(filepath)
        if result:
            result['title'] = f"日报 — {author} — {date}"
            result['author'] = author
            result['date'] = date
            return result
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/weekly")
async def get_weekly_list():
    """获取周报列表"""
    return get_report_list('weekly')


@router.get("/weekly/{year}/{week}/{author}")
async def get_weekly_detail(year: str, week: str, author: str):
    """获取指定周报内容"""
    if not (_YEAR_RE.match(year) and _WEEK_RE.match(week) and _FILENAME_PART_RE.match(author)):
        raise HTTPException(status_code=400, detail="Invalid parameters")

    filepath = _safe_report_path(
        os.path.join(MANAGEMENT_DIR, 'weekly', year),
        f"W{week}-{author}.md",
    )
    if filepath:
        result = get_report_detail(filepath)
        if result:
            result['title'] = f"周报 — {author} — {year} 第 {week} 周"
            result['author'] = author
            result['year'] = year
            result['week'] = week
            return result
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/monthly")
async def get_monthly_list():
    """获取月报列表"""
    return get_report_list('monthly')


@router.get("/monthly/{year}/{month}/{author}")
async def get_monthly_detail(year: str, month: str, author: str):
    """获取指定月报内容"""
    if not (_YEAR_RE.match(year) and _MONTH_RE.match(month) and _FILENAME_PART_RE.match(author)):
        raise HTTPException(status_code=400, detail="Invalid parameters")

    filepath = _safe_report_path(
        os.path.join(MANAGEMENT_DIR, 'monthly', year),
        f"{month}-{author}.md",
    )
    if filepath:
        result = get_report_detail(filepath)
        if result:
            result['title'] = f"月报 — {author} — {year} 年 {month} 月"
            result['author'] = author
            result['year'] = year
            result['month'] = month
            return result
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/tasks")
async def get_tasks(slug: str = None):
    """获取任务看板数据（从 per-project tasks.json 派生，按项目切换）。

    slug 缺省时取首个项目。返回 {in_progress, pending, completed} 三桶。
    """
    return parse_tasks(slug)


@router.get("/milestones")
async def get_milestones():
    """获取里程碑列表"""
    return parse_milestones()


@router.get("/meetings")
async def get_meetings():
    """获取会议纪要列表"""
    meetings_dir = os.path.join(MANAGEMENT_DIR, 'docs', 'meetings')
    files = scan_directory(meetings_dir, pattern=r'.*\.md$')
    files = [f for f in files if 'template' not in os.path.basename(f).lower()]

    meetings = []
    for f in files:
        content = read_file(f)
        if content:
            import re
            # 提取日期
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(f))
            date = date_match.group(1) if date_match else os.path.basename(f)

            # 从内容中提取参会人和记录人
            participants = ''
            recorder = ''
            for line in content.split('\n'):
                if '参会人' in line:
                    participants = line.split('：')[-1].strip() if '：' in line else ''
                if '记录人' in line:
                    recorder = line.split('：')[-1].strip() if '：' in line else ''

            meetings.append({
                'date': date,
                'participants': participants,
                'recorder': recorder,
            })
    return meetings


@router.get("/meetings/{date}")
async def get_meeting_detail(date: str):
    """获取指定会议纪要内容"""
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date")

    meetings_dir = os.path.join(MANAGEMENT_DIR, 'docs', 'meetings')
    filepath = _safe_report_path(meetings_dir, f"{date}.md")
    if filepath:
        content = read_file(filepath)
        if content:
            return {'date': date, 'content': content}
    raise HTTPException(status_code=404, detail="Meeting not found")


# ========== 项目树 ==========

@router.get("/projects")
async def get_projects():
    """获取所有项目列表"""
    return list_projects()


@router.get("/projects/{slug}")
async def get_project_detail(slug: str):
    """获取项目 README 元信息 + 正文"""
    project = get_project(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{slug}/tasks")
async def get_project_tasks_route(slug: str):
    """获取项目任务树"""
    tree = get_project_tasks(slug)
    if tree is None:
        raise HTTPException(status_code=404, detail="Tasks not found")
    return tree


@router.get("/projects/{slug}/notes/{note_path:path}")
async def get_task_note_route(slug: str, note_path: str):
    """获取任务笔记 markdown"""
    content = get_task_note(slug, note_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return {'content': content}
