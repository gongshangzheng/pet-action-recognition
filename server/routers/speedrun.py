"""speed run 路由 — N 视频 × M 模型 → 标注视频 + 聚合结果。

产物（固定格式，由 scripts/speedrun.py 写）：
  results/speedrun/outputs/<model_id>/<video_stem>.mp4   # 帧叠 top-5
  results/speedrun/results.json                          # 聚合所有 model×video
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse

from server.config import (
    SPEEDRUN_DIR,
    SPEEDRUN_OUTPUTS_DIR,
    SPEEDRUN_RESULTS_JSON,
)
from server.utils.file_utils import read_file, safe_resolve

router = APIRouter(prefix="/api/speedrun", tags=["speedrun"])

SPEEDRUN_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "speedrun.py",
)

VIDEO_MIME = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".m4v": "video/x-m4v",
}

IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# 单次 speed run 进程句柄（单机单跑简化；server 重启会丢，但 results.json 持久）
_current_proc: subprocess.Popen | None = None
_current_started_at: str | None = None


@router.post("/run")
async def run_speedrun(data: dict = Body(...)):
    """异步触发 speed run：subprocess 调 scripts/speedrun.py。

    body:
      {videos: [<path>...], models: "all" | [<id>...],
       checkpoint: "pretrained", device: "cuda:0", force: false, labels?: <path>}
    """
    global _current_proc, _current_started_at

    videos = data.get("videos") or []
    if isinstance(videos, str):
        videos = [videos]
    if not videos:
        return {"status": "error", "note": "请提供 videos"}, 400

    models = data.get("models", "all")
    models_args = models if isinstance(models, list) and models else ["all"]
    checkpoint = data.get("checkpoint", "pretrained")
    device = data.get("device", "cuda:0")
    force = bool(data.get("force", False))
    labels = data.get("labels")

    run_id = f"speedrun-{int(time.time())}"
    args = [
        sys.executable, SPEEDRUN_SCRIPT,
        "--videos", *videos,
        "--models", *models_args,
        "--checkpoint", str(checkpoint),
        "--device", str(device),
    ]
    if labels:
        args += ["--labels", str(labels)]
    if force:
        args += ["--force"]

    os.makedirs(SPEEDRUN_DIR, exist_ok=True)
    log_path = os.path.join(SPEEDRUN_DIR, f"{run_id}.log")
    try:
        proc = subprocess.Popen(
            args,
            stdout=open(log_path, "a"),
            stderr=subprocess.STDOUT,
            cwd=str(Path(SPEEDRUN_SCRIPT).resolve().parent.parent),
        )
    except FileNotFoundError as e:
        return {"status": "error", "note": f"脚本未找到: {SPEEDRUN_SCRIPT}", "error": str(e)}

    _current_proc = proc
    _current_started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "status": "started",
        "run_id": run_id,
        "pid": proc.pid,
        "videos": videos,
        "models": models_args,
        "device": device,
        "log": f"results/speedrun/{run_id}.log",
        "note": "speed run 后台运行中；进度见 GET /api/speedrun/results（每 (model,video) 跑完即落盘）。",
    }


@router.get("/results")
async def get_results():
    """读 results/speedrun/results.json（聚合所有 model×video）。"""
    content = read_file(SPEEDRUN_RESULTS_JSON)
    if not content:
        return {"generated_at": None, "results": []}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"generated_at": None, "results": [], "error": "Invalid JSON"}


@router.get("/status")
async def get_status():
    """speed run 是否在跑 + 当前结果计数。"""
    global _current_proc
    running = _current_proc is not None and _current_proc.poll() is None
    data = await get_results()
    return {
        "running": running,
        "pid": _current_proc.pid if running else None,
        "started_at": _current_started_at if running else None,
        "results_count": len(data.get("results", [])),
        "generated_at": data.get("generated_at"),
    }


@router.get("/outputs")
async def list_outputs():
    """列出 SPEEDRUN_OUTPUTS_DIR 下标注视频。"""
    out = []
    if os.path.isdir(SPEEDRUN_OUTPUTS_DIR):
        for root, _, files in os.walk(SPEEDRUN_OUTPUTS_DIR):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                if not os.path.isfile(full) or fn.startswith('.'):
                    continue
                rel = os.path.relpath(full, SPEEDRUN_OUTPUTS_DIR).replace(os.sep, "/")
                ext = os.path.splitext(fn)[1].lower()
                out.append({
                    "name": fn, "path": rel, "ext": ext,
                    "is_video": ext in VIDEO_MIME,
                    "size_bytes": os.path.getsize(full),
                })
    out.sort(key=lambda x: x["path"])
    return {"outputs": out}


@router.get("/outputs/{file_path:path}")
async def serve_output(file_path: str):
    """服务一个标注视频，video MIME，safe_resolve 防穿越。"""
    safe = safe_resolve(SPEEDRUN_OUTPUTS_DIR, file_path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Output not found"}, 404
    ext = os.path.splitext(safe)[1].lower()
    media = VIDEO_MIME.get(ext) or IMAGE_MIME.get(ext) or "application/octet-stream"
    return FileResponse(safe, media_type=media, filename=os.path.basename(safe))
