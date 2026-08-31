#!/usr/bin/env python3
"""arXiv 被限流时的元数据备援：用 OpenAlex（DOI 10.48550/arXiv.*）补全 abstract 与年份。

注意：OpenAlex 的作者姓名存在 given/family 倒序问题（尤其中文姓名），故本脚本
**不写 authors**——作者字段留给 arXiv API（恢复后重跑 scripts/import_papers.py 升级）。

只处理 abstract 为空的记录。用法：
    python3 scripts/backfill_metadata_openalex.py [--dry-run] [--delay 0.8]
"""
import argparse
import json
import sqlite3
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "data" / "papers.db"
OA_API = "https://api.openalex.org/works/https://doi.org/10.48550/arXiv.{arxiv_id}"
HEADERS = {"User-Agent": "pet-action-recognition-papers/1.0 (mailto:research@example.com)"}


def deinvert_abstract(inv: dict | None) -> str:
    """OpenAlex 摘要是倒排索引，重建为文本。"""
    if not inv:
        return ""
    pos = {}
    for word, positions in inv.items():
        for p in positions:
            pos[p] = word
    return " ".join(pos[i] for i in sorted(pos))


def fetch_openalex(arxiv_id: str, max_retries: int = 4) -> dict | None:
    url = OA_API.format(arxiv_id=arxiv_id)
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            wait = 20 if "429" in str(exc) else 6
            print(f"    attempt {attempt + 1} failed: {exc}, wait {wait}s", flush=True)
            time.sleep(wait)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=0.8)
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        """SELECT id, title, external_ids, metadata FROM papers
           WHERE (abstract IS NULL OR abstract = '')"""
    ).fetchall()

    targets = []
    for pid, title, external_ids, metadata in rows:
        arxiv_id = ""
        try:
            arxiv_id = (json.loads(external_ids) or {}).get("arxiv", "")
        except Exception:
            pass
        if not arxiv_id and pid.startswith("arxiv-"):
            arxiv_id = pid[len("arxiv-"):]
        if arxiv_id:
            targets.append((pid, title, arxiv_id, metadata))

    print(f"Found {len(targets)} papers needing metadata backfill", flush=True)
    ok = fail = 0
    for i, (pid, title, arxiv_id, metadata) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] arXiv:{arxiv_id} | {title[:60]}", flush=True)
        data = fetch_openalex(arxiv_id)
        abstract = deinvert_abstract(data.get("abstract_inverted_index")) if data else ""
        if not abstract:
            print("    SKIP (no OpenAlex data / no abstract)", flush=True)
            fail += 1
            time.sleep(args.delay)
            continue
        year = data.get("publication_year")
        published_at = f"{year}-01-01" if year else None
        try:
            meta_obj = json.loads(metadata) if metadata else {}
        except Exception:
            meta_obj = {}
        meta_obj["s2_backfill"] = date.today().isoformat()  # 语义：非 arXiv 来源补全
        meta_obj["metadata_source"] = "openalex"
        meta_obj["published_at_precision"] = "year" if year else None
        if not args.dry_run:
            conn.execute(
                """UPDATE papers SET abstract = ?, published_at = ?, metadata = ?
                   WHERE id = ?""",
                (abstract, published_at, json.dumps(meta_obj, ensure_ascii=False), pid))
            conn.commit()
        ok += 1
        print(f"    OK: {len(abstract)} chars, year={year}", flush=True)
        time.sleep(args.delay)

    print(f"\n=== OpenAlex Backfill Complete === ok={ok}, fail/skip={fail}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
