#!/usr/bin/env python3
"""根据核心论文清单（papers/config/core_papers.json）标记论文库。

- tier=pinned → starred=1, pinned=1（置顶展示）
- tier=core   → starred=1
- 入选理由写入 papers.note（幂等：已有 [核心] 标记不重复追加）

用法：python3 scripts/curate_core_papers.py [--config papers/config/core_papers.json]
"""
import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "data" / "papers.db"
DEFAULT_CONFIG = Path(__file__).parent.parent / "papers" / "config" / "core_papers.json"
MARKER = "[核心]"


def norm_title(title: str) -> str:
    return " ".join(title.lower().replace("&", "and").split())


def match_paper(conn, entry: dict):
    """优先按 arxiv_id（paper id = arxiv-<id>），失败按归一化标题匹配。"""
    arxiv_id = entry.get("arxiv_id", "")
    if arxiv_id:
        row = conn.execute(
            "SELECT id, title, note FROM papers WHERE id = ?",
            (f"arxiv-{arxiv_id}",)).fetchone()
        if row:
            return row
    row = conn.execute(
        "SELECT id, title, note FROM papers WHERE LOWER(title) = LOWER(?)",
        (entry["title"],)).fetchone()
    if row:
        return row
    # 标题归一化兜底（大小写/空白差异）
    for pid, title, note in conn.execute("SELECT id, title, note FROM papers"):
        if norm_title(title) == norm_title(entry["title"]):
            return (pid, title, note)
    return None


def main():
    parser = argparse.ArgumentParser(description="标记核心论文（starred/pinned）")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = json.load(open(args.config))
    conn = sqlite3.connect(str(DB_PATH))

    matched, missing = 0, []
    for entry in config["papers"]:
        row = match_paper(conn, entry)
        if not row:
            missing.append((entry["arxiv_id"] or "-", entry["title"][:60]))
            continue
        paper_id, _title, note = row
        starred = 1
        pinned = 1 if entry.get("tier") == "pinned" else 0
        reason = f"{MARKER} {entry.get('tier', 'core')}: {entry['reason']}（{date.today().isoformat()}）"
        if note and MARKER in note:
            new_note = note  # 已标记过，不重复追加
        elif note:
            new_note = f"{note}\n\n{reason}"
        else:
            new_note = reason
        conn.execute(
            "UPDATE papers SET starred = ?, pinned = ?, note = ? WHERE id = ?",
            (starred, pinned, new_note, paper_id))
        matched += 1
    conn.commit()

    n_pinned = conn.execute("SELECT COUNT(*) FROM papers WHERE pinned = 1").fetchone()[0]
    n_starred = conn.execute("SELECT COUNT(*) FROM papers WHERE starred = 1").fetchone()[0]
    print(f"=== Core Curation Complete ===")
    print(f"Matched & marked: {matched}/{len(config['papers'])}")
    print(f"DB totals: pinned={n_pinned}, starred={n_starred}")
    if missing:
        print(f"\nWARNING: {len(missing)} entries not found in DB:")
        for aid, title in missing:
            print(f"  - ({aid}) {title}")
    conn.close()


if __name__ == "__main__":
    main()
