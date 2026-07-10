"""团队成员 Markdown 解析器"""
import re
from server.utils.file_utils import read_file
from server.parsers.markdown_table import parse_markdown_tables


def parse_team_list(readme_content):
    """从 team/README.md 解析成员列表"""
    if not readme_content:
        return []

    tables = parse_markdown_tables(readme_content)
    if not tables:
        return []

    members = []
    for row in tables[0]:
        members.append({
            'name': row.get('姓名', '').strip(),
            'id': row.get('英文标识', '').strip(),
            'role': row.get('角色', '').strip(),
            'join_date': row.get('入职日期', '').strip(),
        })
    return members


def parse_member_profile(md_content):
    """解析个人档案 Markdown，返回结构化数据"""
    if not md_content:
        return None

    result = {
        'name': '',
        'id': '',
        'role': '',
        'join_date': '',
        'research_direction': '',
        'tech_stack': [],
        'responsible_modules': [],
    }

    # 解析基本信息表格
    tables = parse_markdown_tables(md_content)
    if tables:
        for row in tables[0]:
            field = row.get('字段', '').strip()
            value = row.get('内容', '').strip()
            if field == '姓名':
                result['name'] = value
            elif field == '英文标识':
                result['id'] = value
            elif field == '角色':
                result['role'] = value
            elif field == '入职日期':
                result['join_date'] = value
            elif field == '研究方向':
                result['research_direction'] = value

    # 解析技术栈列表项
    tech_section = _extract_section(md_content, '技术栈')
    if tech_section:
        result['tech_stack'] = _extract_list_items(tech_section)

    # 解析负责模块列表项
    module_section = _extract_section(md_content, '负责模块')
    if module_section:
        result['responsible_modules'] = _extract_list_items(module_section)

    return result


def _extract_section(md_text, section_title):
    """提取指定标题下的内容"""
    pattern = rf'##\s*{re.escape(section_title)}.*?\n(.*?)(?=\n##\s|$)'
    match = re.search(pattern, md_text, re.DOTALL)
    return match.group(1) if match else None


def _extract_list_items(text):
    """从文本中提取 - 开头的列表项"""
    items = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if line.startswith('- '):
            item = line[2:].strip()
            if item and item != '待补充':
                items.append(item)
    return items
