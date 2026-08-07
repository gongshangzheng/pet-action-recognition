"""Live 路由 — 摄像头源管理 + 视频流代理（stream_token）+ 截屏上传。

借鉴 third-party/pet-videos 的 sources.py + security.stream_token，适配本项目。
端点：
  GET    /api/live/sources              列出所有摄像头源
  POST   /api/live/sources              新增源
  PUT    /api/live/sources/{id}         更新源
  DELETE /api/live/sources/{id}         删除源
  GET    /api/live/stream?token=...     凭 stream_token 代理视频流
  GET    /api/live/screenshots          列出截屏（可按 source_id 筛）
  POST   /api/live/screenshots          上传截屏（base64）
"""
from __future__ import annotations

import base64
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from server.config import BASE_DIR, LIVE_DIR
from server.db_live import get_conn, init_db, now_iso
from server.live.security import decode_stream_token, encode_stream_token
from server.utils.file_utils import safe_resolve

router = APIRouter(prefix="/api/live", tags=["live"])

init_db()

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}

LIVE_ANALYZE_SCRIPT = os.path.join(BASE_DIR, "scripts", "live_analyze.py")


# ---------- 请求模型 ----------

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    alias: str = Field(..., min_length=1, max_length=100)
    stream_url: str = Field(..., min_length=1, max_length=1000)
    storage_path: str = Field(..., min_length=1, max_length=1000)
    is_active: bool = True


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    storage_path: Optional[str] = None
    is_active: Optional[bool] = None


class ScreenshotCreate(BaseModel):
    source_id: Optional[int] = None
    filename: str = Field(..., min_length=1, max_length=200)
    note: Optional[str] = None
    data_url: str = Field(..., description="data:image/png;base64,....")


# ---------- 源 CRUD ----------

def _row_to_source(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "alias": row["alias"],
        "stream_url": row["stream_url"],
        "storage_path": row["storage_path"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/sources")
async def list_sources():
    """列出所有摄像头源。"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM stream_sources ORDER BY id").fetchall()
    return {"sources": [_row_to_source(r) for r in rows]}


@router.post("/sources")
async def create_source(body: SourceCreate):
    """新增摄像头源。storage_path 不存在则创建目录。"""
    os.makedirs(body.storage_path, exist_ok=True)
    ts = now_iso()
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO stream_sources (name, alias, stream_url, storage_path, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (body.name, body.alias, body.stream_url, body.storage_path, int(body.is_active), ts, ts),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (cur.lastrowid,)).fetchone()
        except Exception as e:
            raise _db_error(e)
    return {"source": _row_to_source(row)}


@router.put("/sources/{source_id}")
async def update_source(source_id: int, body: SourceUpdate):
    """更新源（部分字段）。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            return {"detail": "Source not found"}, 404
        fields, vals = [], []
        for k in ("name", "stream_url", "storage_path"):
            v = getattr(body, k)
            if v is not None:
                fields.append(f"{k} = ?")
                vals.append(v)
        if body.is_active is not None:
            fields.append("is_active = ?")
            vals.append(int(body.is_active))
        if not fields:
            return {"source": _row_to_source(row)}
        fields.append("updated_at = ?")
        vals.append(now_iso())
        vals.append(source_id)
        conn.execute(f"UPDATE stream_sources SET {', '.join(fields)} WHERE id = ?", vals)
        conn.commit()
        row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (source_id,)).fetchone()
    return {"source": _row_to_source(row)}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int):
    """删除源（不删 storage_path 文件）。"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM stream_sources WHERE id = ?", (source_id,))
        conn.commit()
    if cur.rowcount == 0:
        return {"detail": "Source not found"}, 404
    return {"deleted": source_id}


# ---------- 视频流代理 ----------

@router.get("/sources/{source_id}/files")
async def list_source_files(source_id: int):
    """列出某源 storage_path 下的视频文件（供前端选择播放）。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM stream_sources WHERE id = ?", (source_id,)).fetchone()
    if not row:
        return {"detail": "Source not found"}, 404
    storage = row["storage_path"]
    files = []
    if os.path.isdir(storage):
        for name in sorted(os.listdir(storage)):
            if name.startswith("."):
                continue
            full = os.path.join(storage, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                files.append({"name": name, "size": os.path.getsize(full)})
    return {"alias": row["alias"], "files": files}


@router.get("/play_url")
async def play_url(alias: str = Query(...), filename: str = Query(...)):
    """给前端生成带 stream_token 的播放 url（secret 不外泄，签名在后端）。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM stream_sources WHERE alias = ? AND is_active = 1", (alias,)
        ).fetchone()
    if not row:
        return {"detail": "Source not found or inactive"}, 404
    safe = safe_resolve(row["storage_path"], filename)
    if not safe or not os.path.isfile(safe):
        return {"detail": "File not found"}, 404
    token = encode_stream_token(alias, filename)
    return {"url": f"/api/live/stream?token={token}", "alias": alias, "filename": filename}


@router.get("/stream")
async def stream_video(token: str = Query(..., description="stream_token")):
    """凭 stream_token 代理视频文件（支持 Range）。"""
    alias, filename = decode_stream_token(token)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT storage_path FROM stream_sources WHERE alias = ? AND is_active = 1",
            (alias,),
        ).fetchone()
    if not row:
        return {"detail": "Source not found or inactive"}, 404

    safe = safe_resolve(row["storage_path"], filename)
    if not safe or not os.path.isfile(safe):
        return {"detail": "File not found"}, 404
    return FileResponse(safe, media_type="video/mp4", filename=filename)


# ---------- 实时推理（SSE，同步边播边推）----------

@router.get("/analyze/stream")
async def analyze_stream(
    alias: str = Query(...),
    filename: str = Query(...),
    model_id: str = Query(...),
    model_type: str = Query("mmaction2", description="mmaction2 | vlm"),
    clip_sec: float = Query(1.0, gt=0),
    stride_sec: float = Query(1.0, gt=0),
    device: str = Query("cuda:0"),
):
    """SSE：逐段推理结果。subprocess 调 scripts/live_analyze.py，stdout 行转 SSE。

    每段 yield: data: {"t_start":..,"t_end":..,"label":..,"score":..,"top5":[..],"model":..}
    模型加载/状态也以 {"status":..} 推送。
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT storage_path FROM stream_sources WHERE alias = ? AND is_active = 1",
            (alias,),
        ).fetchone()
    if not row:
        return {"detail": "Source not found or inactive"}, 404
    safe = safe_resolve(row["storage_path"], filename)
    if not safe or not os.path.isfile(safe):
        return {"detail": "File not found"}, 404

    args = [
        sys.executable, LIVE_ANALYZE_SCRIPT,
        "--video", safe, "--model-id", model_id, "--model-type", model_type,
        "--clip-sec", str(clip_sec), "--stride-sec", str(stride_sec),
        "--device", device,
    ]
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(BASE_DIR),
    )

    def gen():
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("{"):
                    yield f"data: {line}\n\n"
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _db_error(e: Exception):
    """把 sqlite 唯一约束冲突转成 409。"""
    msg = str(e)
    if "UNIQUE" in msg.upper():
        return _http(409, "alias already exists")
    return _http(500, f"DB error: {e}")


def _http(status: int, detail: str):
    from fastapi import HTTPException
    return HTTPException(status_code=status, detail=detail)


# ---------- 截屏 ----------

@router.get("/screenshots")
async def list_screenshots(source_id: Optional[int] = None):
    """列出截屏记录（可按 source_id 筛）。"""
    sql = "SELECT * FROM screenshots"
    params: tuple = ()
    if source_id is not None:
        sql += " WHERE source_id = ?"
        params = (source_id,)
    sql += " ORDER BY id DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"screenshots": [dict(r) for r in rows]}


@router.post("/screenshots")
async def create_screenshot(body: ScreenshotCreate):
    """上传截屏（base64 data url），存到对应源的 storage_path/screenshots/。"""
    # 解析 data url
    if "," not in body.data_url:
        return {"detail": "data_url must be 'data:image/...;base64,<...>'"}, 400
    _, b64 = body.data_url.split(",", 1)
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return {"detail": "Invalid base64"}, 400

    # 定位源 storage_path；没源则用默认 screenshots 目录
    from server.config import LIVE_DIR
    if body.source_id:
        with get_conn() as conn:
            row = conn.execute("SELECT storage_path FROM stream_sources WHERE id = ?", (body.source_id,)).fetchone()
        if not row:
            return {"detail": "Source not found"}, 404
        base_dir = os.path.join(row["storage_path"], "screenshots")
    else:
        base_dir = os.path.join(LIVE_DIR, "screenshots")
    os.makedirs(base_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in body.filename)[:80]
    out = os.path.join(base_dir, f"{ts}-{safe_name}.png")
    with open(out, "wb") as f:
        f.write(raw)

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO screenshots (source_id, filename, note, created_at) VALUES (?, ?, ?, ?)",
            (body.source_id, os.path.basename(out), body.note, now_iso()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"screenshot": dict(row)}
