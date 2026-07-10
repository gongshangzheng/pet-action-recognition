"""任务看板 Markdown 解析器"""
import re
from server.utils.file_utils import read_file
from server.config import MANAGEMENT_DIR
from server.parsers.markdown_table import parse_markdown_tables, parse_emoji_status
import os


def parse_tasks(md_content=None):
    """解析 tasks.md，返回三个分组：in_progress, pending, completed"""
    if md_content is None:
        filepath = os.path.join(MANAGEMENT_DIR, 'docs', 'tasks.md')
        md_content = read_file(filepath)

    if not md_content:
        return {'in_progress': [], 'pending': [], 'completed': []}

    tables = parse_markdown_tables(md_content)

    result = {'in_progress': [], 'pending': [], 'completed': []}

    # 按顺序：进行中、待开始、已完成
    section_keys = ['in_progress', 'pending', 'completed']

    for idx, key in enumerate(section_keys):
        if idx < len(tables):
            for row in tables[idx]:
                task = {
                    'name': row.get('任务', '').strip(),
                    'owner': row.get('负责人', '').strip(),
                    'start_date': row.get('开始日期', row.get('预计开始', '')).strip(),
                    'end_date': row.get('截止日期', row.get('完成日期', '')).strip(),
                    'status': parse_emoji_status(row.get('状态', '')),
                    'note': row.get('备注', row.get('产出', '')).strip(),
                }
                if task['name']:
                    result[key].append(task)

    return result
