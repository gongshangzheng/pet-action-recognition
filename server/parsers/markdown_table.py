"""通用 Markdown 表格解析工具"""
import re


def parse_markdown_tables(md_text):
    """解析 Markdown 文本中的所有表格，返回 List[List[Dict]]。

    每个表格解析为 [{col: val, ...}, ...] 的列表。
    多个表格返回为列表的列表。
    """
    if not md_text:
        return []

    tables = []
    lines = md_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        # 检测表格起始行（包含 |）
        if '|' in line and line.startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i].strip() and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                table = _parse_single_table(table_lines)
                if table:
                    tables.append(table)
        else:
            i += 1

    return tables


def _parse_single_table(table_lines):
    """解析单个表格块"""
    if len(table_lines) < 2:
        return []

    # 第一行是表头
    headers = _split_row(table_lines[0])
    if not headers:
        return []

    # 第二行是分隔符（|---|---|）
    if not re.match(r'^\|[\s\-:|]+\|?$', table_lines[1]):
        return []

    rows = []
    for line in table_lines[2:]:
        cells = _split_row(line)
        if cells:
            row = {}
            for idx, header in enumerate(headers):
                row[header.strip()] = cells[idx].strip() if idx < len(cells) else ''
            rows.append(row)

    return rows


def _split_row(line):
    """拆分表格行，返回单元格列表"""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [cell.strip() for cell in line.split('|')]


# Emoji 状态映射
EMOJI_STATUS_MAP = {
    '🟢': 'in_progress',
    '🟡': 'risk',
    '🔴': 'blocked',
    '✅': 'done',
    '⬜': 'pending',
    '✓': 'done',
    '○': 'pending',
}


def parse_emoji_status(text):
    """从文本中解析 emoji 状态标识，返回状态字符串"""
    if not text:
        return 'pending'
    for emoji, status in EMOJI_STATUS_MAP.items():
        if emoji in text:
            return status
    text_lower = text.lower().strip()
    if '完成' in text_lower or 'done' in text_lower or 'completed' in text_lower:
        return 'done'
    if '进行' in text_lower or 'progress' in text_lower:
        return 'in_progress'
    if '延期' in text_lower or 'delay' in text_lower:
        return 'delayed'
    if '阻塞' in text_lower or 'block' in text_lower:
        return 'blocked'
    if '风险' in text_lower or 'risk' in text_lower:
        return 'risk'
    return 'pending'
