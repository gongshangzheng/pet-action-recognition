#!/usr/bin/env python3
"""论文搜索脚本"""

import os
import sys
import sqlite3

DB_PATH = "data/papers.db"

def search_papers(keyword, limit=50):
    """搜索论文"""
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, authors, category, source, starred
        FROM papers
        WHERE title LIKE ? OR authors LIKE ? OR abstract LIKE ? OR category LIKE ?
        ORDER BY starred DESC, created_at DESC
        LIMIT ?
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))

    results = cursor.fetchall()
    conn.close()

    return results

def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else ""
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    if not keyword:
        print("用法: python3 search_papers.py <关键词> [限制数量]")
        sys.exit(1)

    results = search_papers(keyword, limit)

    if not results:
        print(f"未找到包含 '{keyword}' 的论文")
        return

    print(f"找到 {len(results)} 篇论文:\n")
    for row in results:
        paper_id, title, authors, category, source, starred = row
        star = "⭐" if starred else " "
        print(f"{star} [{paper_id}]")
        print(f"   标题: {title}")
        print(f"   作者: {authors}")
        print(f"   分类: {category} | 来源: {source}")
        print()

if __name__ == "__main__":
    main()
