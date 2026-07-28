"""数据集管理路由 — 浏览 datasets/ 目录、分页、视频封面图、文件预览。

端点：
  GET /api/datasets                          列出所有数据集
  GET /api/datasets/{dataset_id}/browse      浏览内容（分页，子目录 + 文件）
  GET /api/datasets/{dataset_id}/file        服务文件（图片/视频）
  GET /api/datasets/{dataset_id}/thumb       视频封面图（按需提取中间帧 + 缓存）
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from server.config import DATASETS_DIR
from server.utils.file_utils import safe_resolve

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

VIDEO_MIME = {".mp4": "video/mp4", ".avi": "video/x-msvideo", ".mov": "video/quicktime",
              ".mkv": "video/x-matroska", ".webm": "video/webm", ".m4v": "video/x-m4v"}
IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
              ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}

THUMBS_DIR = os.path.join(DATASETS_DIR, ".thumbs")


def _dataset_path(dataset_id: str) -> str | None:
    """解析 dataset_id 到绝对路径（datasets/<id>，可能是软链）。"""
    p = os.path.join(DATASETS_DIR, dataset_id)
    return p if os.path.isdir(p) else None


@router.get("")
async def list_datasets():
    """列出 datasets/ 下所有数据集（含软链）。"""
    out = []
    if os.path.isdir(DATASETS_DIR):
        for name in sorted(os.listdir(DATASETS_DIR)):
            if name.startswith("."):
                continue
            full = os.path.join(DATASETS_DIR, name)
            if not os.path.isdir(full):
                continue
            is_link = os.path.islink(full)
            real = os.path.realpath(full) if is_link else full
            # 统计子目录数 + 文件数（浅扫，不递归）
            subdirs = 0
            files = 0
            try:
                for entry in os.listdir(full):
                    if os.path.isdir(os.path.join(full, entry)):
                        subdirs += 1
                    else:
                        files += 1
            except OSError:
                pass
            out.append({
                "id": name,
                "name": name,
                "path": f"datasets/{name}",
                "is_symlink": is_link,
                "real_path": real if is_link else None,
                "subdirs": subdirs,
                "files": files,
            })
    return {"datasets": out}


@router.get("/{dataset_id}/browse")
async def browse(
    dataset_id: str,
    path: str = Query("", description="相对路径（子目录），空=根目录"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """浏览数据集内容（分页）。返回子目录 + 文件。"""
    base = _dataset_path(dataset_id)
    if not base:
        return {"detail": "Dataset not found"}, 404
    safe = safe_resolve(base, path)
    if not safe or not os.path.isdir(safe):
        return {"detail": "Path not found"}, 404

    # 收集所有条目
    items = []
    try:
        for name in sorted(os.listdir(safe)):
            if name.startswith("."):
                continue
            full = os.path.join(safe, name)
            is_dir = os.path.isdir(full)
            ext = os.path.splitext(name)[1].lower()
            items.append({
                "name": name,
                "type": "dir" if is_dir else "file",
                "ext": ext if not is_dir else None,
                "is_video": ext in VIDEO_EXTS,
                "is_image": ext in IMAGE_EXTS,
                "size_bytes": os.path.getsize(full) if not is_dir else None,
            })
    except OSError:
        pass

    # 分页
    total = len(items)
    start = (page - 1) * size
    page_items = items[start:start + size]
    return {
        "dataset_id": dataset_id,
        "path": path,
        "items": page_items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 0,
    }


@router.get("/{dataset_id}/file")
async def serve_file(
    dataset_id: str,
    path: str = Query(..., description="相对文件路径"),
):
    """服务一个文件（图片/视频），带正确 MIME。"""
    base = _dataset_path(dataset_id)
    if not base:
        return {"detail": "Dataset not found"}, 404
    safe = safe_resolve(base, path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "File not found"}, 404
    ext = os.path.splitext(safe)[1].lower()
    media = VIDEO_MIME.get(ext) or IMAGE_MIME.get(ext) or "application/octet-stream"
    return FileResponse(safe, media_type=media, filename=os.path.basename(safe))


@router.get("/{dataset_id}/thumb")
async def serve_thumb(
    dataset_id: str,
    path: str = Query(..., description="相对视频文件路径"),
):
    """生成 + 缓存视频封面图（中间帧 JPG），后续请求直接返回缓存。"""
    base = _dataset_path(dataset_id)
    if not base:
        return {"detail": "Dataset not found"}, 404
    safe = safe_resolve(base, path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "File not found"}, 404

    # 缓存路径：.thumbs/<md5(绝对路径)>.jpg
    os.makedirs(THUMBS_DIR, exist_ok=True)
    key = hashlib.md5(safe.encode()).hexdigest()[:16]
    thumb_path = os.path.join(THUMBS_DIR, f"{key}.jpg")

    if not os.path.isfile(thumb_path):
        # 提取中间帧
        try:
            import cv2
            cap = cv2.VideoCapture(safe)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 2:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
            ok, frame = cap.read()
            cap.release()
            if ok and frame is not None:
                cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            else:
                return {"detail": "Failed to extract frame"}, 500
        except Exception as e:
            return {"detail": f"Thumbnail error: {e}"}, 500

    if os.path.isfile(thumb_path):
        return FileResponse(thumb_path, media_type="image/jpeg")
    return {"detail": "Thumbnail not generated"}, 500
