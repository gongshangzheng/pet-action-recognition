"""Live 模块数据库 — 摄像头源 + 截屏记录，独立 SQLite 存储。

借鉴 third-party/pet-videos 的 StreamSource 表结构，适配本项目原生 sqlite3 风格。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from server.config import LIVE_DIR

DB_PATH = Path(LIVE_DIR) / "live.db"


def get_conn() -> sqlite3.Connection:
    """获取 live.db 连接（Row 工厂 + 外键）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化 stream_sources + screenshots 表。"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stream_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                alias TEXT NOT NULL UNIQUE,
                stream_url TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                filename TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES stream_sources(id) ON DELETE SET NULL
            );
        """)
        conn.commit()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
