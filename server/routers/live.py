"""Live 路由 — 示例视频演示 + 截屏 + 摄像头源管理。

端点：
  GET    /api/live/demo/videos          列出演示视频
  GET    /api/live/demo/video/{name}    流式服务演示视频
  GET    /api/live/demo/analyze/stream  SSE 演示推理
  GET    /api/live/screenshots          列出截屏
  POST   /api/live/screenshots          上传截屏（base64）
  GET    /api/live/sources              列出摄像头源
  POST   /api/live/sources              添加摄像头源
  PUT    /api/live/sources/{id}         更新摄像头源
  DELETE /api/live/sources/{id}         删除摄像头源
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

from server.config import BASE_DIR, LIVE_DIR, LIVE_DEMO_DIR
from server.db_live import (
    get_conn, init_db, now_iso,
    get_stream_sources, get_stream_source,
    create_stream_source, update_stream_source, delete_stream_source,
)
from server.utils.file_utils import safe_resolve

router = APIRouter(prefix="/api/live", tags=["live"])

# 视频文件扩展名
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}

LIVE_ANALYZE_SCRIPT = os.path.join(BASE_DIR, "scripts", "live_analyze.py")

init_db()


# ---------- 请求模型 ----------

class ScreenshotCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    note: Optional[str] = None
    data_url: str = Field(..., description="data:image/png;base64,....")


# ---------- 截屏 ----------

@router.get("/screenshots")
async def list_screenshots():
    """列出截屏记录。"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM screenshots ORDER BY id DESC").fetchall()
    return {"screenshots": [dict(r) for r in rows]}


# ---------- 摄像头源管理 ----------

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    alias: str = ""
    stream_url: str = Field(..., min_length=1)
    storage_path: str = ""


class SourceUpdate(BaseModel):
    name: str = ""
    alias: str = ""
    stream_url: str = ""
    storage_path: str = ""
    is_active: bool = True


@router.get("/sources")
async def list_sources():
    return {"sources": get_stream_sources()}


@router.post("/sources", status_code=201)
async def add_source(body: SourceCreate):
    src = create_stream_source(
        name=body.name,
        stream_url=body.stream_url,
        alias=body.alias,
        storage_path=body.storage_path,
    )
    return {"source": src}


@router.put("/sources/{source_id}")
async def edit_source(source_id: int, body: SourceUpdate):
    fields = {k: v for k, v in body.model_dump().items() if v}
    src = update_stream_source(source_id, **fields)
    if not src:
        return {"detail": "Source not found"}, 404
    return {"source": src}


@router.delete("/sources/{source_id}", status_code=204)
async def remove_source(source_id: int):
    ok = delete_stream_source(source_id)
    if not ok:
        return {"detail": "Source not found"}, 404


@router.post("/screenshots")
async def create_screenshot(body: ScreenshotCreate):
    """上传截屏（base64 data url），存到 live/screenshots/。"""
    if "," not in body.data_url:
        return {"detail": "data_url must be 'data:image/...;base64,<...>'"}, 400
    _, b64 = body.data_url.split(",", 1)
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return {"detail": "Invalid base64"}, 400

    base_dir = os.path.join(LIVE_DIR, "screenshots")
    os.makedirs(base_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in body.filename)[:80]
    out = os.path.join(base_dir, f"{ts}-{safe_name}.png")
    with open(out, "wb") as f:
        f.write(raw)

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO screenshots (filename, note, created_at) VALUES (?, ?, ?)",
            (os.path.basename(out), body.note, now_iso()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"screenshot": dict(row)}


# ---------- 演示模式（Demo）----------

@router.get("/demo/videos")
async def list_demo_videos():
    """列出演示视频（从 live/demos/ 目录）。"""
    if not os.path.isdir(LIVE_DEMO_DIR):
        return {"videos": []}
    videos = []
    for name in sorted(os.listdir(LIVE_DEMO_DIR)):
        if name.startswith("."):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in VIDEO_EXTS:
            continue
        full = os.path.join(LIVE_DEMO_DIR, name)
        # 从文件名提取标签（如 locomotion-xxx.mp4 → locomotion）
        parts = name.replace(ext, "").split("-")
        label = parts[0] if parts else name
        videos.append({
            "name": name,
            "label": label,
            "size": os.path.getsize(full),
        })
    return {"videos": videos}


@router.get("/demo/video/{video_name}")
async def serve_demo_video(video_name: str):
    """流式服务演示视频（无需 token）。"""
    safe = safe_resolve(LIVE_DEMO_DIR, video_name)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Video not found"}, 404
    ext = os.path.splitext(video_name)[1].lower()
    mime = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
    }.get(ext, "video/mp4")
    return FileResponse(safe, media_type=mime, filename=video_name)


@router.get("/demo/analyze/stream")
async def demo_analyze_stream(
    video_name: str = Query(...),
    model_id: str = Query(...),
    model_type: str = Query("mmaction2"),
    clip_sec: float = Query(1.0, gt=0),
    stride_sec: float = Query(1.0, gt=0),
    device: str = Query("cuda:0"),
):
    """SSE 演示推理：对 demo 视频逐段推理并流式返回结果。"""
    safe = safe_resolve(LIVE_DEMO_DIR, video_name)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Video not found"}, 404

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


# ---------- 真直播流（帧级同步：视频帧 + 推理结果走同一条 SSE）----------

LIVE_STREAM_SCRIPT = os.path.join(BASE_DIR, "scripts", "live_stream.py")


@router.get("/demo/live_stream")
async def demo_live_stream(
    video_name: str = Query(...),
    model_id: str = Query(...),
    stride_sec: float = Query(0.5, gt=0),
    clip_sec: float = Query(1.0, gt=0),
    device: str = Query("cuda:0"),
):
    import logging
    logger = logging.getLogger("uvicorn.error")
    logger.warning(f"[live_stream] video={video_name} model={model_id} device={device}")
    """真直播流：同时推送视频帧（base64 JPEG）和推理结果，帧级同步。

    推送格式（SSE data 行）：
      {"type": "frame", "t": 0.0, "fps": 30.0, "width": 640, "height": 360, "data_url": "data:image/jpeg;base64,..."}
      {"type": "result", "t": 0.0, "label": "locomotion", "score": 0.92, ...}
      {"type": "status", "status": "loading_model", ...}
      {"type": "done"}
    """
    safe = safe_resolve(LIVE_DEMO_DIR, video_name)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Video not found"}, 404

    args = [
        sys.executable, LIVE_STREAM_SCRIPT,
        "--video", safe,
        "--model-id", model_id,
        "--stride-sec", str(stride_sec),
        "--clip-sec", str(clip_sec),
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
