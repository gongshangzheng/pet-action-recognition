#!/usr/bin/env python3
"""Inspect, convert and explicitly publish article-note figures."""
import argparse
import shutil
import sys
from pathlib import Path

MAX_EDGE = 1600
MAX_FILE = 500 * 1024
MAX_TOTAL = 5 * 1024 * 1024
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def image_info(path):
    try:
        from PIL import Image
        with Image.open(path) as image:
            return image.size, image.format
    except ImportError:
        return None, "Pillow unavailable"
    except Exception as exc:
        return None, str(exc)


def inspect(directory):
    paths = sorted(path for path in Path(directory).rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    total = 0
    failed = False
    for path in paths:
        size, fmt = image_info(path)
        bytes_count = path.stat().st_size
        total += bytes_count
        warning = []
        if bytes_count > MAX_FILE:
            warning.append("over 500KB")
        if size and max(size) > MAX_EDGE:
            warning.append("long edge over 1600px")
        if fmt == "Pillow unavailable":
            warning.append("dimensions unavailable")
        if warning:
            failed = True
        print("%s | %s bytes | %s | %s" % (path, bytes_count, size or "?", ", ".join(warning) or "OK"))
    print("total_bytes:", total)
    if total > MAX_TOTAL:
        print("ERROR: total exceeds 5MB")
        failed = True
    return 1 if failed else 0


def convert(input_dir, output_dir, quality, dry_run=False):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("WARNING: Pillow unavailable; copying original files", file=sys.stderr)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        for path in Path(input_dir).rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                shutil.copy2(path, Path(output_dir) / path.name)
        return 0
    if not dry_run:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    for source in sorted(Path(input_dir).rglob("*")):
        if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if dry_run:
            print("would convert:", source, "->", Path(output_dir) / (source.stem + ".webp"))
            continue
        with Image.open(source) as image:
            image = image.convert("RGB")
            if max(image.size) > MAX_EDGE:
                scale = MAX_EDGE / float(max(image.size))
                image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.LANCZOS)
            output = Path(output_dir) / (source.stem + ".webp")
            image.save(output, "WEBP", quality=quality, method=6)
            print(output)
    return inspect(output_dir)


def publish(input_dir, slug, docs_root, dry_run):
    destination = Path(docs_root) / "_assets" / slug
    paths = sorted(path for path in Path(input_dir).rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    if not paths:
        print("没有可发布的图片", file=sys.stderr)
        return 1
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    total = 0
    failed = False
    for index, source in enumerate(paths, 1):
        target_name = source.name
        target = destination / target_name
        total += source.stat().st_size
        if source.stat().st_size > MAX_FILE:
            print("ERROR:", source, "超过 500KB", file=sys.stderr)
            failed = True
        url = "/api/management/docs-assets/%s/%s" % (slug, target_name)
        print("![图 %d · %s](%s)" % (index, source.stem.replace("-", " "), url))
        if not dry_run:
            shutil.copy2(source, target)
    if total > MAX_TOTAL:
        print("ERROR: 总体积超过 5MB", file=sys.stderr)
        failed = True
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description="article-note 图片检查、转换和发布")
    sub = parser.add_subparsers(dest="command", required=True)
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--input", required=True)
    p_convert = sub.add_parser("convert")
    p_convert.add_argument("--input", required=True)
    p_convert.add_argument("--output", required=True)
    p_convert.add_argument("--quality", type=int, default=82)
    p_convert.add_argument("--dry-run", action="store_true")
    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--input", required=True)
    p_publish.add_argument("--slug", required=True)
    p_publish.add_argument("--docs-root", default="management/docs")
    p_publish.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "inspect":
        return inspect(args.input)
    if args.command == "convert":
        return convert(args.input, args.output, args.quality, args.dry_run)
    return publish(args.input, args.slug, args.docs_root, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
