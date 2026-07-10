"""论文搜集路由 — 代理到 SeekVerse API"""
import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Request, Response
from fastapi.responses import StreamingResponse
from server.config import SEEKVERSE_BASE

router = APIRouter(prefix="/api/papers", tags=["papers"])

_client = httpx.AsyncClient(base_url=SEEKVERSE_BASE, timeout=30.0)

# ========== 本地收藏/置顶存储 ==========

_FAV_PATH = Path("data/paper_favorites.json")


def _load_favs() -> dict:
    """加载本地收藏/置顶数据。"""
    if _FAV_PATH.exists():
        return json.loads(_FAV_PATH.read_text(encoding="utf-8"))
    return {}


def _save_favs(favs: dict) -> None:
    """保存收藏/置顶数据。"""
    _FAV_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FAV_PATH.write_text(json.dumps(favs, ensure_ascii=False, indent=2), encoding="utf-8")


def _enrich_local(paper_dict: dict) -> dict:
    """为论文 dict 附加本地 starred/pinned 状态。"""
    favs = _load_favs()
    pid = paper_dict.get("id", "")
    fav = favs.get(pid, {})
    paper_dict["starred"] = fav.get("starred", False)
    paper_dict["pinned"] = fav.get("pinned", False)
    return paper_dict


@router.get("")
async def list_papers(request: Request):
    """获取论文列表 — 代理 SeekVerse，附加本地收藏/置顶状态"""
    params = dict(request.query_params)
    resp = await _client.get("/api/papers", params=params)
    data = resp.json()
    for p in data.get("papers", []):
        _enrich_local(p)
    return data


@router.get("/stats/summary")
async def get_stats():
    """获取论文统计 — 代理 SeekVerse"""
    resp = await _client.get("/api/papers/stats/summary")
    return resp.json()


@router.post("/fetch")
async def fetch_paper(url: str = Body(..., embed=True), force: bool = Body(False, embed=True)):
    """通过 URL 拉取论文 — 代理 SeekVerse"""
    resp = await _client.post("/api/papers/fetch", json={"url": url, "force": force})
    return resp.json()


@router.get("/{paper_id}")
async def get_paper_detail(paper_id: str):
    """获取论文详情 — 代理 SeekVerse，附加本地收藏/置顶状态"""
    resp = await _client.get(f"/api/papers/{paper_id}")
    data = resp.json()
    return _enrich_local(data)


@router.get("/{paper_id}/note")
async def get_paper_note(paper_id: str):
    """获取论文笔记 — 代理 SeekVerse"""
    resp = await _client.get(f"/api/papers/{paper_id}/note")
    return resp.json()


@router.put("/{paper_id}/note")
async def save_paper_note(paper_id: str, content: str = Body(..., embed=True)):
    """保存论文笔记 — 代理 SeekVerse"""
    resp = await _client.put(f"/api/papers/{paper_id}/note", json={"content": content})
    return resp.json()


@router.put("/{paper_id}/blog")
async def set_blog_url(paper_id: str, blog_url: str = Body(..., embed=True)):
    """设置论文 blog 链接 — 代理 SeekVerse"""
    resp = await _client.put(f"/api/papers/{paper_id}/blog", json={"blog_url": blog_url})
    return resp.json()


@router.post("/{paper_id}/summarize")
async def summarize_paper(paper_id: str):
    """触发论文摘要生成 — 代理 SeekVerse"""
    resp = await _client.post(f"/api/papers/{paper_id}/summarize")
    return resp.json()


# ========== 收藏 / 置顶 ==========

@router.put("/{paper_id}/star")
async def toggle_star(paper_id: str, starred: bool = Body(..., embed=True)):
    """收藏 / 取消收藏论文。"""
    favs = _load_favs()
    if paper_id not in favs:
        favs[paper_id] = {}
    favs[paper_id]["starred"] = starred
    _save_favs(favs)
    return {"status": "ok", "starred": starred}


@router.put("/{paper_id}/pin")
async def toggle_pin(paper_id: str, pinned: bool = Body(..., embed=True)):
    """置顶 / 取消置顶论文。"""
    favs = _load_favs()
    if paper_id not in favs:
        favs[paper_id] = {}
    favs[paper_id]["pinned"] = pinned
    _save_favs(favs)
    return {"status": "ok", "pinned": pinned}


# ========== 缩略图代理 ==========

@router.get("/thumbnails/{arxiv_id}")
async def get_thumbnail(arxiv_id: str):
    """获取论文缩略图 — 代理 SeekVerse。

    SeekVerse 在缩略图不存在时返回 JSON 错误（状态码 200），
    需要检查 content-type 判断是否为真实图片。
    """
    # 尝试 webp
    resp = await _client.get(f"/thumbnails/{arxiv_id}.webp")
    ct = resp.headers.get("content-type", "")
    if resp.status_code == 200 and "image" in ct:
        return Response(content=resp.content, media_type="image/webp")

    # 尝试 png
    resp = await _client.get(f"/thumbnails/{arxiv_id}.png")
    ct = resp.headers.get("content-type", "")
    if resp.status_code == 200 and "image" in ct:
        return Response(content=resp.content, media_type="image/png")

    return Response(content=b"", media_type="image/png", status_code=404)


# ========== Digest 代理 ==========

@router.get("/digests/daily")
async def get_daily_digest():
    """获取今日论文 digest — 代理 SeekVerse"""
    resp = await _client.get("/api/digests/daily")
    return resp.json()


@router.post("/digests/generate")
async def generate_digest(period: str = "今日", limit: int = 100):
    """生成论文 digest — 代理 SeekVerse"""
    resp = await _client.post("/api/digests/generate", params={"period": period, "limit": limit})
    return resp.json()
