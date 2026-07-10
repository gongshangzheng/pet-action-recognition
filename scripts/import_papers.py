#!/usr/bin/env python3
"""从博客提取的论文列表导入到 SeekVerse 数据库。

1. 清空现有论文
2. 从 arXiv API 批量获取论文元数据
3. 写入 SeekVerse SQLite 数据库
"""
import json
import sqlite3
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "seekverse" / "data" / "seekverse.db"
PAPERS_JSON = Path(__file__).parent.parent / "data" / "extracted_papers.json"
ARXIV_API = "http://export.arxiv.org/api/query"

# arXiv API namespace
NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv_batch(arxiv_ids: list[str]) -> dict:
    """从 arXiv API 批量获取论文元数据。"""
    results = {}
    # arXiv API 限制每次最多 100 个，我们分批
    batch_size = 50
    for i in range(0, len(arxiv_ids), batch_size):
        batch = arxiv_ids[i:i + batch_size]
        id_list = ",".join(batch)
        params = urllib.parse.urlencode({
            "id_list": id_list,
            "max_results": len(batch),
        })
        url = f"{ARXIV_API}?{params}"
        print(f"  Fetching arXiv batch {i//batch_size + 1}: {len(batch)} papers...")

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        for entry in root.findall("atom:entry", NS):
            # 从 entry 的 id URL 提取 arXiv ID
            entry_id = entry.find("atom:id", NS).text
            # 格式: http://arxiv.org/abs/2203.12602v1
            arxiv_id = entry_id.split("/abs/")[-1]
            # 去除版本号
            if "v" in arxiv_id:
                base, _, ver = arxiv_id.rpartition("v")
                if ver.isdigit():
                    arxiv_id = base

            title = entry.find("atom:title", NS).text.strip().replace("\n", " ")
            # 清理多余空白
            title = " ".join(title.split())

            summary = entry.find("atom:summary", NS).text.strip().replace("\n", " ")
            summary = " ".join(summary.split())

            published = entry.find("atom:published", NS).text.strip()

            authors = []
            for author in entry.findall("atom:author", NS):
                name = author.find("atom:name", NS)
                if name is not None:
                    authors.append(name.text.strip())
            authors_json = json.dumps(authors, ensure_ascii=False)

            # 获取分类
            categories = []
            for cat in entry.findall("atom:category", NS):
                term = cat.get("term", "")
                if term:
                    categories.append(term)

            # PDF URL
            pdf_url = ""
            for link in entry.findall("atom:link", NS):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break

            results[arxiv_id] = {
                "title": title,
                "abstract": summary,
                "authors": authors_json,
                "published_at": published,
                "pdf_url": pdf_url,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "categories": categories,
            }

        # arXiv API 要求每 3 秒最多一次请求
        if i + batch_size < len(arxiv_ids):
            time.sleep(3)

    return results


def generate_paper_id(arxiv_id: str) -> str:
    """生成论文 ID（与 SeekVerse 格式一致）。"""
    return f"arxiv-{arxiv_id}"


def insert_paper(conn, paper_data: dict, extracted: dict):
    """插入一篇论文到数据库。"""
    arxiv_id = extracted.get("arxiv_id", "")
    paper_id = generate_paper_id(arxiv_id) if arxiv_id else f"manual-{hash(extracted['title']) % 10**12}"

    title = paper_data.get("title", extracted["title"])
    abstract = paper_data.get("abstract", "")
    # authors 必须是 JSON 数组格式（SeekVerse _row_to_paper 用 json.loads 解析）
    authors_raw = paper_data.get("authors", "")
    if authors_raw and isinstance(authors_raw, str) and authors_raw.startswith("["):
        authors = authors_raw  # 已经是 JSON 数组字符串
    elif authors_raw:
        # 逗号分隔的字符串，转为 JSON 数组
        author_list = [a.strip() for a in authors_raw.split(",") if a.strip()]
        authors = json.dumps(author_list, ensure_ascii=False)
    else:
        authors = json.dumps(["Unknown"])
    # published_at 必须是有效的 ISO 日期或 None
    published_at = paper_data.get("published_at", "")
    if not published_at:
        published_at = None
    pdf_url = paper_data.get("pdf_url", "")
    url = paper_data.get("url", extracted.get("url", ""))
    categories = paper_data.get("categories", [])

    # 映射 arXiv 分类到我们的分类体系
    our_categories = map_categories(categories, extracted)

    external_ids = json.dumps({"arxiv": arxiv_id}) if arxiv_id else "{}"
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT OR REPLACE INTO papers
           (id, title, title_zh, abstract, abstract_zh, authors,
            published_at, crawled_at, url, pdf_url, source, external_ids,
            summary_zh, relevance_score, llm_classification, metadata,
            arxiv_categories, starred, pinned)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        (
            paper_id,
            title,
            extracted.get("title_zh", ""),
            abstract,
            "",  # abstract_zh
            authors,
            published_at,
            now,
            url,
            pdf_url,
            "arxiv" if arxiv_id else "manual",
            external_ids,
            "",  # summary_zh
            0.5,  # relevance_score
            json.dumps(our_categories),  # llm_classification
            json.dumps({"source_article": extracted.get("source_article", ""), "role": extracted.get("role", "")}),
            json.dumps(categories),
        )
    )

    # 插入分类关联
    for cat in our_categories:
        conn.execute(
            "INSERT OR IGNORE INTO paper_categories (paper_id, category) VALUES (?, ?)",
            (paper_id, cat),
        )


def map_categories(arxiv_categories: list, extracted: dict) -> list:
    """将 arXiv 分类映射到我们的分类体系。"""
    cats = set()

    # 根据来源文章和角色推断分类
    source = extracted.get("source_article", "")
    title_lower = extracted["title"].lower()

    # 动作识别核心
    cats.add("action_recognition")

    # 宠物/动物相关
    if any(kw in source or kw in title_lower for kw in
           ["pet", "animal", "cat", "dog", "behavior", "behaviour", "kingdom", "mammal",
            "deeplabcut", "superanimal", "pmmnet", "animalk", "apt", "animer", "posebridge"]):
        cats.add("pet_action_recognition")

    # 骨架动作识别
    if any(kw in title_lower for kw in ["skeleton", "skeletal", "graph", "st-gcn", "skeletr", "igmn"]):
        cats.add("skeleton_action_recognition")

    # 视频基础模型
    if any(kw in title_lower for kw in
           ["videomae", "videomamba", "internvideo", "v-jepa", "mvit", "timesformer",
            "vivit", "video swin", "video foundation", "masked autoencoder"]):
        cats.add("video_foundation_model")

    # 姿态估计
    if any(kw in title_lower for kw in
           ["pose", "keypoint", "deeplabcut", "animer", "openpose", "mmpose"]):
        cats.add("pose_estimation")

    # 时序动作检测
    if any(kw in title_lower for kw in
           ["temporal action", "action detection", "action localization", "tad"]):
        cats.add("temporal_action_detection")

    # 综述
    if any(kw in title_lower for kw in ["survey", "review", "benchmark"]):
        cats.add("survey")

    if not cats:
        cats.add("action_recognition")

    return list(cats)


def main():
    # 1. 读取提取的论文
    print(f"Reading {PAPERS_JSON}...")
    with open(PAPERS_JSON) as f:
        extracted_papers = json.load(f)
    print(f"  Found {len(extracted_papers)} papers")

    papers_with_arxiv = [p for p in extracted_papers if p.get("arxiv_id")]
    papers_without_arxiv = [p for p in extracted_papers if not p.get("arxiv_id")]
    print(f"  With arXiv ID: {len(papers_with_arxiv)}")
    print(f"  Without arXiv ID: {len(papers_without_arxiv)}")

    # 2. 从 arXiv API 获取元数据
    arxiv_ids = [p["arxiv_id"] for p in papers_with_arxiv]
    print(f"\nFetching metadata from arXiv API for {len(arxiv_ids)} papers...")
    arxiv_metadata = fetch_arxiv_batch(arxiv_ids)
    print(f"  Got metadata for {len(arxiv_metadata)} papers")

    # 检查哪些没获取到
    missing = [aid for aid in arxiv_ids if aid not in arxiv_metadata]
    if missing:
        print(f"  WARNING: {len(missing)} papers not found on arXiv API:")
        for aid in missing:
            print(f"    - {aid}")

    # 3. 连接数据库
    print(f"\nConnecting to {DB_PATH}...")
    conn = sqlite3.connect(str(DB_PATH))

    # 4. 清空现有论文
    print("Clearing existing papers...")
    conn.execute("DELETE FROM paper_categories")
    conn.execute("DELETE FROM papers")
    conn.commit()
    print("  Done")

    # 5. 插入有 arXiv ID 的论文
    print(f"\nInserting {len(papers_with_arxiv)} papers with arXiv ID...")
    inserted = 0
    for extracted in papers_with_arxiv:
        arxiv_id = extracted["arxiv_id"]
        metadata = arxiv_metadata.get(arxiv_id, {})
        if not metadata:
            print(f"  SKIP (no arXiv metadata): {arxiv_id} - {extracted['title'][:50]}")
            continue
        insert_paper(conn, metadata, extracted)
        inserted += 1
    conn.commit()
    print(f"  Inserted: {inserted}")

    # 6. 插入没有 arXiv ID 的论文
    print(f"\nInserting {len(papers_without_arxiv)} papers without arXiv ID...")
    for extracted in papers_without_arxiv:
        # 构造基本元数据
        # authors 转为 JSON 数组格式
        raw_authors = extracted.get("authors", "Unknown")
        if raw_authors and isinstance(raw_authors, str):
            author_list = [a.strip() for a in raw_authors.split(",") if a.strip()]
            authors_json = json.dumps(author_list, ensure_ascii=False)
        else:
            authors_json = json.dumps(["Unknown"])
        metadata = {
            "title": extracted["title"],
            "abstract": "",
            "authors": authors_json,
            "published_at": "",
            "pdf_url": "",
            "url": extracted.get("url", ""),
            "categories": [],
        }
        # 如果有 DOI，构造 DOI URL
        if extracted.get("doi"):
            metadata["url"] = f"https://doi.org/{extracted['doi']}"
        insert_paper(conn, metadata, extracted)
    conn.commit()
    print(f"  Inserted: {len(papers_without_arxiv)}")

    # 7. 统计
    cursor = conn.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    cursor = conn.execute("SELECT category, COUNT(*) FROM paper_categories GROUP BY category ORDER BY COUNT(*) DESC")
    cat_stats = cursor.fetchall()

    print(f"\n=== Import Complete ===")
    print(f"Total papers in database: {total}")
    print(f"\nCategory distribution:")
    for cat, count in cat_stats:
        print(f"  {cat}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
