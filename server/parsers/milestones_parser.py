"""里程碑 Markdown 解析器"""
import os
from server.utils.file_utils import read_file
from server.config import MANAGEMENT_DIR
from server.parsers.markdown_table import parse_markdown_tables, parse_emoji_status


def parse_milestones(md_content=None):
    """解析 milestones.md，返回里程碑列表"""
    if md_content is None:
        filepath = os.path.join(MANAGEMENT_DIR, 'milestones.md')
        md_content = read_file(filepath)

    if not md_content:
        return []

    tables = parse_markdown_tables(md_content)
    if not tables:
        return []

    milestones = []
    for row in tables[0]:
        m = {
            'name': row.get('里程碑', '').strip(),
            'target_date': row.get('目标日期', '').strip(),
            'actual_date': row.get('实际完成', '').strip(),
            'status': parse_emoji_status(row.get('状态', '')),
            'owner': row.get('负责人', '').strip(),
            'description': row.get('说明', '').strip(),
        }
        if m['name']:
            # 处理 "-" 表示无值
            if m['actual_date'] == '-':
                m['actual_date'] = ''
            milestones.append(m)

    return milestones
