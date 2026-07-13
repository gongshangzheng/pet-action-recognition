import os
import re


def safe_resolve(base_dir, *parts):
    """安全地拼接并解析路径，确保结果位于 base_dir 内部（含符号链接解析）。"""
    if not isinstance(base_dir, str):
        return None
    try:
        base = os.path.realpath(base_dir)
        if not os.path.isdir(base):
            return None
        path = os.path.realpath(os.path.join(base, *parts))
        # 允许等于 base 目录，或位于 base 之下
        if path != base and not path.startswith(base + os.sep):
            return None
        return path
    except (ValueError, OSError):
        return None


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
