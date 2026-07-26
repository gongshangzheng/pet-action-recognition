#!/usr/bin/env python3
"""下载 mmaction2 pretrained checkpoint 到本地缓存。

用法：
  python3 scripts/download_checkpoint.py                       # 列出所有可用模型
  python3 scripts/download_checkpoint.py --model-id tsn-resnet50
  python3 scripts/download_checkpoint.py --all                # 批量下载全部
  python3 scripts/download_checkpoint.py --model-id tsn-resnet50 --force

镜像回退：
  - openmmlab 直链（pet 实测可达）
  - 失败重试 3 次（指数退避）
  - huggingface.co URL 自动走 hf-mirror.com（国内镜像）

产物：
  results/training/pretrained/<model_id>.pth       # 权重
  results/training/pretrained/<model_id>.pth.json   # 元数据（url, sha256, size, time）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import PRETRAINED_CACHE_DIR
from server.routers.training import _MMACTION2_REGISTRY

CHUNK = 1 << 20  # 1 MB
RETRIES = 3
TIMEOUT = 60


def _hf_mirror(url: str) -> str:
    """huggingface.co → hf-mirror.com（国内镜像）。"""
    return url.replace("://huggingface.co/", "://hf-mirror.com/") if "://huggingface.co/" in url else url


def _download(url: str, dst: str, force: bool = False) -> tuple[bool, str, str | None]:
    """下载 url → dst。返回 (ok, msg, sha256)。"""
    if os.path.isfile(dst) and not force:
        return True, "skip (exists)", None
    url = _hf_mirror(url)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mmaction2-dl/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(tmp, "wb") as f:
                h = hashlib.sha256()
                while True:
                    chunk = r.read(CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
            os.replace(tmp, dst)
            return True, "ok", h.hexdigest()
        except (urllib.error.URLError, OSError) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(2 * attempt)
    if os.path.exists(tmp):
        os.remove(tmp)
    return False, f"fail: {last_err}", None


def _write_meta(model: dict, path: str, sha256: str | None) -> None:
    meta = {
        "model_id": model["id"],
        "name": model.get("name", ""),
        "family": model.get("family", ""),
        "pretrained_source": model.get("pretrained_source", ""),
        "url": model["pretrained_url"],
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "size_bytes": os.path.getsize(path) if os.path.isfile(path) else 0,
        "sha256": sha256,
    }
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download mmaction2 pretrained checkpoints")
    parser.add_argument("--model-id", help="model id from registry (e.g. tsn-resnet50)")
    parser.add_argument("--all", action="store_true", help="download all models in registry")
    parser.add_argument("--force", action="store_true", help="re-download even if file exists")
    parser.add_argument("--out-dir", default=PRETRAINED_CACHE_DIR,
                        help=f"cache dir (default: {PRETRAINED_CACHE_DIR})")
    parser.add_argument("--list", action="store_true", help="list registry and exit")
    args = parser.parse_args()

    if args.list or (not args.model_id and not args.all):
        print(f"{'model_id':30s}  {'name':30s}  pretrained_url")
        print("-" * 100)
        for m in _MMACTION2_REGISTRY:
            print(f"{m['id']:30s}  {m.get('name','')[:30]:30s}  {m.get('pretrained_url','')[:50]}")
        return 0

    targets = _MMACTION2_REGISTRY if args.all else [m for m in _MMACTION2_REGISTRY if m["id"] == args.model_id]
    if not targets:
        print(f"[error] unknown model_id: {args.model_id}")
        print("        run with --list to see available models")
        return 1

    print(f"Downloading {len(targets)} checkpoint(s) to {args.out_dir}")
    failures: list[str] = []
    for m in targets:
        url = m.get("pretrained_url")
        if not url:
            print(f"[skip] {m['id']}: no pretrained_url")
            continue
        dst = os.path.join(args.out_dir, f"{m['id']}.pth")
        print(f"[{m['id']}] {url}")
        ok, msg, sha = _download(url, dst, args.force)
        if ok:
            _write_meta(m, dst, sha)
            size = os.path.getsize(dst) if os.path.isfile(dst) else 0
            print(f"  -> {dst}  ({msg}, {size // (1 << 20)} MB)")
        else:
            print(f"  -> {msg}")
            failures.append(m["id"])

    if failures:
        print(f"\nFailed: {failures}")
        return 1
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
