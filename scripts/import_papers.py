#!/usr/bin/env python3
"""从论文候选 JSON 导入到本地论文数据库（幂等，可重复执行）。

1. 读取候选 JSON（默认 data/extracted_papers.json，可用 --input 指定）
2. 从 arXiv API 批量获取论文元数据（失败重试，仍失败则降级 manual 通道）
3. 幂等写入 SQLite（data/papers.db）：
   - 新记录：INSERT 完整字段
   - 已有记录：仅更新派生元数据字段，保留 starred/pinned/note/blog_url 等用户数据
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# 确保能 import server 模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from server.db import init_db

DB_PATH = Path(__file__).parent.parent / "data" / "papers.db"
DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "extracted_papers.json"
ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")

# arXiv API namespace
NS = {"atom": "http://www.w3.org/2005/Atom"}


def stable_manual_id(title: str) -> str:
    """按标题生成稳定 ID（Python 内建 hash 跨进程随机，不能用于幂等去重）。"""
    normalized = " ".join(title.lower().split())
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"manual-{digest}"


def fetch_arxiv_batch(arxiv_ids: list, max_retries: int = 2) -> tuple:
    """从 arXiv API 批量获取论文元数据；单批失败重试后放弃该批（调用方降级处理）。"""
    results = {}
    failed_batches = []
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

        xml_data = None
        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    xml_data = resp.read().decode("utf-8")
                break
            except Exception as exc:
                print(f"    attempt {attempt + 1} failed: {exc}")
                if attempt < max_retries:
                    time.sleep(5)
        if xml_data is None:
            print(f"    WARNING: batch {i//batch_size + 1} failed after retries, "
                  f"{len(batch)} ids fall back to manual channel")
            failed_batches.extend(batch)
            continue

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

    return results, failed_batches


def build_paper_id(arxiv_id: str, title: str) -> str:
    """有合法 arXiv ID 用 arxiv-<id>，否则用稳定 manual ID。"""
    if arxiv_id and ARXIV_ID_RE.match(arxiv_id):
        return f"arxiv-{arxiv_id}"
    return stable_manual_id(title)


def normalize_authors(authors_raw) -> str:
    """authors 必须是 JSON 数组格式（db.py row_to_dict 用 json.loads 解析）。"""
    if isinstance(authors_raw, list):
        return json.dumps(authors_raw, ensure_ascii=False)
    if authors_raw and isinstance(authors_raw, str) and authors_raw.startswith("["):
        return authors_raw  # 已经是 JSON 数组字符串
    if authors_raw:
        author_list = [a.strip() for a in authors_raw.split(",") if a.strip()]
        return json.dumps(author_list, ensure_ascii=False)
    return json.dumps(["Unknown"])


def upsert_paper(conn, paper_data: dict, extracted: dict):
    """幂等写入一篇论文：新记录 INSERT，已有记录仅更新派生元数据。"""
    arxiv_id = extracted.get("arxiv_id", "")
    if arxiv_id and not ARXIV_ID_RE.match(arxiv_id):
        print(f"    WARNING: invalid arxiv_id format '{arxiv_id}', treat as manual: "
              f"{extracted['title'][:50]}")
        arxiv_id = ""
    paper_id = build_paper_id(arxiv_id, extracted["title"])

    title = paper_data.get("title", extracted["title"])
    abstract = paper_data.get("abstract", "")
    authors = normalize_authors(paper_data.get("authors", ""))
    published_at = paper_data.get("published_at", "") or None
    pdf_url = paper_data.get("pdf_url", "")
    url = paper_data.get("url", extracted.get("url", ""))
    categories = paper_data.get("categories", [])
    now = datetime.now().isoformat()

    # 映射 arXiv 分类到我们的分类体系
    our_categories = map_categories(categories, extracted)
    # 候选 JSON 可显式指定分类（调研论文按专题分组）
    explicit_category = extracted.get("category")
    if explicit_category and explicit_category not in our_categories:
        our_categories = [explicit_category] + our_categories

    external_ids = json.dumps({"arxiv": arxiv_id}) if arxiv_id else "{}"
    metadata = json.dumps({
        "source_article": extracted.get("source_article", ""),
        "role": extracted.get("role", ""),
    }, ensure_ascii=False)

    existing = conn.execute(
        "SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if existing:
        # 仅更新派生元数据；保留 title_zh/abstract_zh/summary_zh/relevance_score/
        # llm_classification/starred/pinned/blog_url/note 等用户或已有数据
        conn.execute(
            """UPDATE papers SET
               title = ?, abstract = ?, authors = ?, published_at = ?,
               crawled_at = ?, url = ?, pdf_url = ?, source = ?,
               external_ids = ?, metadata = ?, arxiv_categories = ?
               WHERE id = ?""",
            (title, abstract, authors, published_at, now, url, pdf_url,
             "arxiv" if arxiv_id else "manual", external_ids, metadata,
             json.dumps(categories), paper_id))
    else:
        conn.execute(
            """INSERT INTO papers
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
                metadata,
                json.dumps(categories),
            )
        )

    # 插入分类关联
    for cat in our_categories:
        conn.execute(
            "INSERT OR IGNORE INTO paper_categories (paper_id, category) VALUES (?, ?)",
            (paper_id, cat))


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
    parser = argparse.ArgumentParser(description="导入论文候选 JSON 到 papers.db（幂等）")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"候选 JSON 文件（默认 {DEFAULT_INPUT.name}）")
    args = parser.parse_args()

    # 1. 读取候选论文
    print(f"Reading {args.input}...")
    with open(args.input) as f:
        extracted_papers = json.load(f)
    print(f"  Found {len(extracted_papers)} papers")

    # arXiv ID 合法性校验：非法 ID 直接走 manual 通道
    papers_with_arxiv = [p for p in extracted_papers
                         if p.get("arxiv_id") and ARXIV_ID_RE.match(p["arxiv_id"])]
    invalid_id_papers = [p for p in extracted_papers
                         if p.get("arxiv_id") and not ARXIV_ID_RE.match(p["arxiv_id"])]
    papers_without_arxiv = [p for p in extracted_papers if not p.get("arxiv_id")]
    print(f"  With valid arXiv ID: {len(papers_with_arxiv)}")
    print(f"  Without arXiv ID: {len(papers_without_arxiv)}")
    if invalid_id_papers:
        print(f"  Invalid arXiv ID (fallback to manual): {len(invalid_id_papers)}")

    # 2. 从 arXiv API 获取元数据
    arxiv_ids = [p["arxiv_id"] for p in papers_with_arxiv]
    print(f"\nFetching metadata from arXiv API for {len(arxiv_ids)} papers...")
    arxiv_metadata, failed_ids = fetch_arxiv_batch(arxiv_ids)
    if failed_ids:
        print(f"  WARNING: {len(failed_ids)} ids failed (network), fall back to manual channel")
    print(f"  Got metadata for {len(arxiv_metadata)} papers")

    # 检查哪些没获取到（ID 错误或撤稿等）
    missing = [aid for aid in arxiv_ids
               if aid not in arxiv_metadata and aid not in failed_ids]
    if missing:
        print(f"  WARNING: {len(missing)} papers not found on arXiv API (fall back to manual):")
        for aid in missing:
            print(f"    - {aid}")

    # 3. 初始化并连接数据库
    init_db()  # 创建表结构（如果不存在）
    print(f"\nConnecting to {DB_PATH}...")
    conn = sqlite3.connect(str(DB_PATH))
    before = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    print(f"  Papers in DB before: {before}")

    # 4. 幂等写入有 arXiv ID 的论文（元数据缺失的降级 manual 通道）
    print(f"\nUpserting {len(papers_with_arxiv)} papers with arXiv ID...")
    upserted = 0
    skipped = []
    for extracted in papers_with_arxiv:
        arxiv_id = extracted["arxiv_id"]
        metadata = arxiv_metadata.get(arxiv_id, {})
        if not metadata:
            # arXiv 查不到：降级 manual 入库（保留条目本身，不丢弃）
            skipped.append((arxiv_id, extracted["title"]))
            metadata = {
                "title": extracted["title"],
                "abstract": "",
                "authors": extracted.get("authors", ""),
                "published_at": "",
                "pdf_url": "",
                "url": extracted.get("url", ""),
                "categories": [],
            }
            print(f"  FALLBACK manual (no arXiv metadata): {arxiv_id} - {extracted['title'][:50]}")
        upsert_paper(conn, metadata, extracted)
        upserted += 1
    conn.commit()
    print(f"  Processed: {upserted} (fallback: {len(skipped)})")

    # 5. 写入没有 arXiv ID 的论文
    print(f"\nUpserting {len(papers_without_arxiv) + len(invalid_id_papers)} papers without arXiv ID...")
    for extracted in papers_without_arxiv + invalid_id_papers:
        extracted = dict(extracted)
        extracted["arxiv_id"] = ""  # 强制 manual 通道
        metadata = {
            "title": extracted["title"],
            "abstract": "",
            "authors": extracted.get("authors", ""),
            "published_at": "",
            "pdf_url": "",
            "url": extracted.get("url", ""),
            "categories": [],
        }
        # 如果有 DOI，构造 DOI URL
        if extracted.get("doi"):
            metadata["url"] = f"https://doi.org/{extracted['doi']}"
        upsert_paper(conn, metadata, extracted)
    conn.commit()

    # 6. 统计
    cursor = conn.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    cursor = conn.execute(
        "SELECT category, COUNT(*) FROM paper_categories GROUP BY category ORDER BY COUNT(*) DESC")
    cat_stats = cursor.fetchall()

    print(f"\n=== Import Complete ===")
    print(f"Papers in database: {before} -> {total}")
    print(f"\nCategory distribution:")
    for cat, count in cat_stats:
        print(f"  {cat}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
