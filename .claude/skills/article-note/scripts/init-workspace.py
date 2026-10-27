#!/usr/bin/env python3
"""Initialize an article-note workspace without overwriting existing files."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def valid_slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("slug 不能为空")
    return slug


def write_if_missing(path, content, force=False):
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="初始化 article-note 工作区")
    parser.add_argument("slug", help="论文 slug，例如 maskgit-2022")
    parser.add_argument("--root", default=".cache/article-note", help="工作区根目录")
    parser.add_argument("--check", action="store_true", help="只检查，不创建文件")
    parser.add_argument("--force", action="store_true", help="覆盖工作区骨架文件，不删除已有材料")
    args = parser.parse_args()

    try:
        slug = valid_slug(args.slug)
    except ValueError as exc:
        parser.error(str(exc))
    workspace = Path(args.root).expanduser().resolve() / slug
    directories = [workspace / "raw" / "sources", workspace / "raw" / "figures", workspace / "analysis"]
    files = {
        workspace / "raw" / "sources" / "extraction-log.md": "# Extraction Log\n\n尚未开始抓取。\n",
        workspace / "raw" / "figures" / "figures-manifest.md": "# Figures Manifest\n\n尚未登记候选图片。\n",
        workspace / "synthesis.md": "# Synthesis\n\n尚未完成分析。\n",
    }
    manifest = workspace / "workspace.json"
    if args.check:
        missing = [str(path) for path in directories + list(files) + [manifest] if not path.exists()]
        if missing:
            print("MISSING")
            print("\n".join(missing))
            return 1
        print("OK", workspace)
        return 0

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    created = 0
    for path, content in files.items():
        if write_if_missing(path, content, args.force):
            created += 1
    if not manifest.exists() or args.force:
        manifest.write_text(json.dumps({
            "slug": slug,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "workspace": str(workspace),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created += 1
    print("workspace:", workspace)
    print("created_or_updated:", created)
    return 0


if __name__ == "__main__":
    sys.exit(main())
