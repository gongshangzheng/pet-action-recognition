#!/usr/bin/env python3
"""导入论文到 SQLite 数据库"""

import os
import sys
import json
import sqlite3
from datetime import datetime

DB_PATH = "data/papers.db"

def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT,
            abstract TEXT,
            source TEXT DEFAULT 'custom',
            category TEXT DEFAULT '',
            published_date TEXT,
            starred INTEGER DEFAULT 0,
            pinned INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            blog_url TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    return conn

def import_papers(papers_json):
    """导入论文"""
    conn = init_db()
    cursor = conn.cursor()

    count = 0
    for paper in papers_json:
        cursor.execute('''
            INSERT OR REPLACE INTO papers
            (id, title, authors, abstract, source, category, published_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (
            paper.get('id', ''),
            paper.get('title', ''),
            paper.get('authors', ''),
            paper.get('abstract', ''),
            paper.get('source', 'custom'),
            paper.get('category', ''),
            paper.get('published_date', '')
        ))
        count += 1

    conn.commit()
    conn.close()
    return count

def import_from_file(filepath):
    """从文件导入"""
    with open(filepath, 'r', encoding='utf-8') as f:
        if filepath.endswith('.json'):
            papers = json.load(f)
        else:
            print(f"不支持的文件格式: {filepath}")
            return 0

    if not isinstance(papers, list):
        print("JSON 文件必须包含一个论文数组")
        return 0

    return import_papers(papers)

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 import_papers.py <papers.json>")
        print("示例:")
        print("  python3 import_papers.py papers.json")
        sys.exit(1)

    filepath = sys.argv[1]
    count = import_from_file(filepath)
    print(f"✓ 成功导入 {count} 篇论文")

if __name__ == "__main__":
    main()
