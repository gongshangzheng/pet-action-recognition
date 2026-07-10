import os
import re


def scan_directory(base_dir, pattern=None):
    """递归扫描目录，返回匹配的文件列表"""
    if not os.path.exists(base_dir):
        return []

    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.startswith('.'):
                continue
            if pattern is None or re.match(pattern, f):
                results.append(os.path.join(root, f))
    return sorted(results)


def read_file(filepath):
    """读取文件内容，返回字符串"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def safe_list_dir(base_dir):
    """安全列出目录内容"""
    if not os.path.exists(base_dir):
        return []
    return [f for f in os.listdir(base_dir) if not f.startswith('.')]
