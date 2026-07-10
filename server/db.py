"""论文数据库模块 — 独立于 SeekVerse 的本地 SQLite 存储。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "papers.db"


def get_conn() -> sqlite3.Connection:
    """获取数据库连接（启用外键 + Row 工厂）。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化数据库表结构。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            title_zh TEXT,
            abstract TEXT,
            abstract_zh TEXT,
            authors TEXT NOT NULL DEFAULT '[]',
            published_at TEXT,
            crawled_at TEXT,
            url TEXT NOT NULL DEFAULT '',
            pdf_url TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            external_ids TEXT NOT NULL DEFAULT '{}',
            summary_zh TEXT,
            relevance_score REAL DEFAULT 0.5,
            llm_classification TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            arxiv_categories TEXT DEFAULT '[]',
            starred INTEGER DEFAULT 0,
            pinned INTEGER DEFAULT 0,
            blog_url TEXT,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS paper_categories (
            paper_id TEXT REFERENCES papers(id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            PRIMARY KEY (paper_id, category)
        );

        CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
        CREATE INDEX IF NOT EXISTS idx_paper_categories_cat ON paper_categories(category);
    """)
    conn.commit()
    conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """将数据库行转换为前端 API 格式的 dict。"""
    if row is None:
        return None

    d = dict(row)

    # JSON 字段解析
    for field in ("authors", "external_ids", "llm_classification", "metadata", "arxiv_categories"):
        val = d.get(field)
        if isinstance(val, str):
            try:
                d[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[field] = [] if field in ("authors", "llm_classification", "arxiv_categories") else {}
        elif val is None:
            d[field] = [] if field in ("authors", "llm_classification", "arxiv_categories") else {}

    # 布尔字段
    d["starred"] = bool(d.get("starred", 0))
    d["pinned"] = bool(d.get("pinned", 0))

    # 加载分类
    conn = get_conn()
    cat_rows = conn.execute(
        "SELECT category FROM paper_categories WHERE paper_id = ?", (d["id"],)
    ).fetchall()
    conn.close()
    d["categories"] = [r["category"] for r in cat_rows]

    # has_note 字段
    d["has_note"] = bool(d.get("note"))

    return d


def query_papers(
    source: str | None = None,
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "published_at DESC",
) -> tuple[list[dict], int]:
    """查询论文列表，返回 (papers, total)。"""
    conn = get_conn()
    sql = "SELECT DISTINCT p.* FROM papers p"
    params: list = []

    if category:
        sql += " JOIN paper_categories pc ON p.id = pc.paper_id"

    conditions = []
    if source:
        conditions.append("p.source = ?")
        params.append(source)
    if category:
        conditions.append("pc.category = ?")
        params.append(category)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    # 总数
    count_sql = f"SELECT COUNT(DISTINCT p.id) FROM papers p"
    if category:
        count_sql += " JOIN paper_categories pc ON p.id = pc.paper_id"
    if conditions:
        count_sql += " WHERE " + " AND ".join(conditions)
    total = conn.execute(count_sql, params).fetchone()[0]

    # 分页查询
    sql += f" ORDER BY p.{order_by} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    papers = [row_to_dict(row) for row in rows]
    return papers, total


def get_paper_by_id(paper_id: str) -> dict | None:
    """根据 ID 获取单篇论文。"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_stats() -> dict:
    """获取统计信息。"""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    by_source = {
        row[0]: row[1]
        for row in conn.execute("SELECT source, COUNT(*) FROM papers GROUP BY source").fetchall()
    }
    by_category = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT category, COUNT(*) FROM paper_categories GROUP BY category"
        ).fetchall()
    }
    conn.close()
    return {"total": total, "by_source": by_source, "by_category": by_category}


def set_starred(paper_id: str, starred: bool) -> None:
    conn = get_conn()
    conn.execute("UPDATE papers SET starred = ? WHERE id = ?", (int(starred), paper_id))
    conn.commit()
    conn.close()


def set_pinned(paper_id: str, pinned: bool) -> None:
    conn = get_conn()
    conn.execute("UPDATE papers SET pinned = ? WHERE id = ?", (int(pinned), paper_id))
    conn.commit()
    conn.close()


def get_note(paper_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT note FROM papers WHERE id = ?", (paper_id,)).fetchone()
    conn.close()
    return {"content": row["note"] if row and row["note"] else ""}


def save_note(paper_id: str, content: str) -> dict:
    conn = get_conn()
    conn.execute("UPDATE papers SET note = ? WHERE id = ?", (content, paper_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def set_blog_url(paper_id: str, blog_url: str) -> dict:
    conn = get_conn()
    conn.execute("UPDATE papers SET blog_url = ? WHERE id = ?", (blog_url, paper_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def upsert_paper(paper_data: dict) -> None:
    """插入或更新论文。"""
    conn = get_conn()
    authors = paper_data.get("authors", [])
    if isinstance(authors, list):
        authors = json.dumps(authors, ensure_ascii=False)

    external_ids = paper_data.get("external_ids", {})
    if isinstance(external_ids, dict):
        external_ids = json.dumps(external_ids, ensure_ascii=False)

    arxiv_categories = paper_data.get("arxiv_categories", [])
    if isinstance(arxiv_categories, list):
        arxiv_categories = json.dumps(arxiv_categories, ensure_ascii=False)

    llm_classification = paper_data.get("llm_classification", [])
    if isinstance(llm_classification, list):
        llm_classification = json.dumps(llm_classification, ensure_ascii=False)

    metadata = paper_data.get("metadata", {})
    if isinstance(metadata, dict):
        metadata = json.dumps(metadata, ensure_ascii=False)

    conn.execute(
        """INSERT OR REPLACE INTO papers
           (id, title, title_zh, abstract, abstract_zh, authors,
            published_at, crawled_at, url, pdf_url, source, external_ids,
            summary_zh, relevance_score, llm_classification, metadata,
            arxiv_categories, starred, pinned, blog_url, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            paper_data["id"],
            paper_data["title"],
            paper_data.get("title_zh", ""),
            paper_data.get("abstract", ""),
            paper_data.get("abstract_zh", ""),
            authors,
            paper_data.get("published_at", ""),
            paper_data.get("crawled_at", datetime.now().isoformat()),
            paper_data.get("url", ""),
            paper_data.get("pdf_url", ""),
            paper_data.get("source", "manual"),
            external_ids,
            paper_data.get("summary_zh", ""),
            paper_data.get("relevance_score", 0.5),
            llm_classification,
            metadata,
            arxiv_categories,
            int(paper_data.get("starred", False)),
            int(paper_data.get("pinned", False)),
            paper_data.get("blog_url", ""),
            paper_data.get("note", ""),
        ),
    )

    # 分类
    categories = paper_data.get("categories", [])
    if categories:
        conn.execute("DELETE FROM paper_categories WHERE paper_id = ?", (paper_data["id"],))
        for cat in categories:
            conn.execute(
                "INSERT OR IGNORE INTO paper_categories (paper_id, category) VALUES (?, ?)",
                (paper_data["id"], cat),
            )

    conn.commit()
    conn.close()
