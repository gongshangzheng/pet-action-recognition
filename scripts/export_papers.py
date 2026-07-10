#!/usr/bin/env python3
"""导出论文数据为静态 JSON，供 GitHub Pages 部署使用。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from server.db import init_db, query_papers

OUTPUT = Path(__file__).parent.parent / "web" / "public" / "data" / "papers.json"


def main():
    init_db()
    papers, total = query_papers(limit=500, offset=0)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"total": total, "papers": papers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {total} papers to {OUTPUT}")


if __name__ == "__main__":
    main()
