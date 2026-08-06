"""Live 模块 stream_token 安全签名 — 抄 third-party/pet-videos/backend/utils/security.py。

token = base64url(alias:filename).sha256(data + LIVE_SECRET)[:16]
解码时校验签名，防止伪造路径越权访问。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from pathlib import Path

from fastapi import HTTPException

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}


def _secret() -> str:
    """从环境变量读 LIVE_SECRET，缺失时用仓库内默认值（开发用，生产必须配 env）。"""
    return os.environ.get("LIVE_SECRET", "pet-action-recognition-live-dev-secret")


def encode_stream_token(alias: str, filename: str) -> str:
    """生成 (alias:filename) 的签名 token。"""
    data = f"{alias}:{filename}"
    sig = hmac.new(_secret().encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    encoded = base64.urlsafe_b64encode(data.encode()).decode()
    return f"{encoded}.{sig}"


def decode_stream_token(token: str) -> tuple[str, str]:
    """校验签名并返回 (alias, filename)；失败抛 403。"""
    try:
        encoded, sig = token.rsplit(".", 1)
        data = base64.urlsafe_b64decode(encoded.encode()).decode("utf-8")
        alias, filename = data.split(":", 1)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid stream token")

    expected = hmac.new(_secret().encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="Invalid stream token signature")

    # 扩展名白名单 + 防穿越
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=403, detail=f"Extension not allowed: {ext}")
    if os.sep in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=403, detail="Filename must not contain path separators")
    return alias, filename
