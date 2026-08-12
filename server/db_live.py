"""Live 模块数据库 — 截屏记录。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from server.config import LIVE_DIR

DB_PATH = Path(LIVE_DIR) / "live.db"


def get_conn() -> sqlite3.Connection:
    """获取 live.db 连接（Row 工厂）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化 screenshots + stream_sources 表。"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stream_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                alias TEXT,
                stream_url TEXT NOT NULL,
                storage_path TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------- stream_sources ----------

def get_stream_sources() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM stream_sources ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_stream_source(id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM stream_sources WHERE id = ?", (id,)
        ).fetchone()
    return dict(row) if row else None


def create_stream_source(name: str, stream_url: str, alias: str = "", storage_path: str = "") -> dict:
    now = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO stream_sources (name, alias, stream_url, storage_path, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (name, alias, stream_url, storage_path, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def update_stream_source(id: int, **fields) -> dict | None:
    allowed = {"name", "alias", "stream_url", "storage_path", "is_active"}
    sets = ", ".join(f"{k} = ?" for k in fields if k in allowed)
    if not sets:
        return get_stream_source(id)
    vals = [fields[k] for k in fields if k in allowed]
    vals.append(now_iso())
    vals.append(id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE stream_sources SET {sets}, updated_at = ? WHERE id = ?",
            vals,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


def delete_stream_source(id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM stream_sources WHERE id = ?", (id,))
        conn.commit()
    return cur.rowcount > 0
