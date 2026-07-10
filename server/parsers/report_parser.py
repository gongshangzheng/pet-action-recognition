"""报告 Markdown 解析器（日报/周报/月报通用）"""
import re
import os
from server.utils.file_utils import scan_directory, read_file
from server.config import MANAGEMENT_DIR


def parse_report_metadata(filepath, report_type):
    """从文件路径解析报告元数据"""
    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]

    if report_type == 'daily':
        # 格式: YYYY-MM-DD-姓名.md 或 DD-姓名.md (在 YYYY/MM/ 目录下)
        match = re.match(r'(\d{2})-(.+)$', name_no_ext)
        if match:
            # 从路径中提取年月
            parts = filepath.replace('\\', '/').split('/')
            year = month = day = ''
            author = match.group(2)
            day = match.group(1)
            for p in parts:
                if re.match(r'^\d{4}$', p):
                    year = p
                elif re.match(r'^\d{2}$', p):
                    month = p
            date_str = f"{year}-{month}-{day}" if year and month else day
            return {
                'id': filepath,
                'date': date_str,
                'author': author,
                'title': f"日报 — {author} — {date_str}",
                'year': year,
                'month': month,
            }
    elif report_type == 'weekly':
        # 格式: WXX-姓名.md
        match = re.match(r'(W\d+)-(.+)$', name_no_ext)
        if match:
            parts = filepath.replace('\\', '/').split('/')
            year = ''
            for p in parts:
                if re.match(r'^\d{4}$', p):
                    year = p
            week = match.group(1)
            author = match.group(2)
            return {
                'id': filepath,
                'year': year,
                'week': week.lstrip('W'),
                'author': author,
                'title': f"周报 — {author} — {year} 第 {week} 周",
            }
    elif report_type == 'monthly':
        # 格式: MM-姓名.md (在 YYYY/ 目录下)
        match = re.match(r'(\d{2})-(.+)$', name_no_ext)
        if match:
            parts = filepath.replace('\\', '/').split('/')
            year = ''
            for p in parts:
                if re.match(r'^\d{4}$', p):
                    year = p
            month = match.group(1)
            author = match.group(2)
            return {
                'id': filepath,
                'year': year,
                'month': month,
                'author': author,
                'title': f"月报 — {author} — {year} 年 {month} 月",
            }

    return None


def get_report_list(report_type):
    """获取报告列表"""
    base_dir = os.path.join(MANAGEMENT_DIR, report_type)
    if not os.path.exists(base_dir):
        return []

    # 扫描 .md 文件，排除 template.md
    files = scan_directory(base_dir, pattern=r'.*\.md$')
    files = [f for f in files if 'template' not in os.path.basename(f).lower()]

    reports = []
    for f in files:
        meta = parse_report_metadata(f, report_type)
        if meta:
            reports.append(meta)

    return reports


def get_report_detail(filepath):
    """获取报告详情（含内容）"""
    content = read_file(filepath)
    if content is None:
        return None
    return {'content': content}
