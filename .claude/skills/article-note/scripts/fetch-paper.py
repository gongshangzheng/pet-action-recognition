#!/usr/bin/env python3
"""Fetch arXiv source/HTML/PDF into an article-note workspace.

The script is intentionally conservative: it only writes under --workspace.
"""
import argparse
import json
import re
import shutil
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".gif", ".bmp", ".tiff", ".tif"}


def parse_arxiv_id(value):
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", value)
    if match:
        return match.group(1)
    match = re.search(r"([a-z-]+\.[A-Z]+/\d{7}(?:v\d+)?)", value)
    return match.group(1) if match else value.strip()


def request_bytes(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "ProjFlow article-note/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def safe_extract(tar_path, output):
    output_resolved = output.resolve()
    with tarfile.open(tar_path, "r:*") as archive:
        for member in archive.getmembers():
            target = (output / member.name).resolve()
            if output_resolved not in target.parents and target != output_resolved:
                raise RuntimeError("tar archive contains unsafe path: %s" % member.name)
        archive.extractall(output)


def tex_text(source):
    tex_files = sorted(source.rglob("*.tex"))
    if not tex_files:
        return ""
    chunks = []
    for path in tex_files:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(content.strip()) >= 20:
            chunks.append("%% === %s ===\n%s" % (path.name, content))
    text = "\n\n".join(chunks)
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(r"\\section\*?\{([^{}]+)\}", r"## \1", text)
    text = re.sub(r"\\subsection\*?\{([^{}]+)\}", r"### \1", text)
    text = re.sub(r"\\subsubsection\*?\{([^{}]+)\}", r"#### \1", text)
    text = re.sub(r"\\text(?:bf|it|tt|emph)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def extract_metadata(source, arxiv_id):
    metadata = {"arxiv_id": arxiv_id}
    readme = source / "00README.json"
    if readme.exists():
        try:
            data = json.loads(readme.read_text(encoding="utf-8"))
            metadata.update({key: data.get(key) for key in ("title", "abstract", "authors") if data.get(key)})
        except (OSError, ValueError):
            pass
    for tex in sorted(source.rglob("*.tex")):
        try:
            content = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "title" not in metadata:
            match = re.search(r"\\title\*?\{([^{}]+)\}", content)
            if match:
                metadata["title"] = match.group(1).strip()
        if "authors" not in metadata:
            match = re.search(r"\\author\*?\{([^{}]+)\}", content)
            if match:
                metadata["authors"] = match.group(1).strip()
        if "title" in metadata and "authors" in metadata:
            break
    return metadata


def copy_figures(source, figures_dir):
    found = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        destination = figures_dir / path.name
        if destination.exists():
            destination = figures_dir / (path.stem + "-" + str(len(found) + 1) + path.suffix.lower())
        shutil.copy2(path, destination)
        found.append(destination.name)
    return found


def main():
    parser = argparse.ArgumentParser(description="抓取 arXiv 论文材料到 article-note 工作区")
    parser.add_argument("--input", required=True, help="arXiv ID 或 URL")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    arxiv_id = parse_arxiv_id(args.input)
    workspace = Path(args.workspace).expanduser().resolve()
    sources = workspace / "raw" / "sources"
    figures = workspace / "raw" / "figures"
    log_path = sources / "extraction-log.md"
    if args.dry_run:
        print("arxiv_id:", arxiv_id)
        print("workspace:", workspace)
        print("would_fetch: source, html=%s, pdf=%s" % (args.html, args.pdf))
        return 0
    sources.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    source_ok = False
    html_ok = False
    pdf_ok = False
    notes = []
    source_tar = workspace / "raw" / "source.tar"
    source_dir = workspace / "raw" / "source-tar"
    try:
        source_tar.write_bytes(request_bytes("https://arxiv.org/e-print/" + arxiv_id, args.timeout))
        source_dir.mkdir(exist_ok=True)
        safe_extract(source_tar, source_dir)
        source_ok = True
        metadata = extract_metadata(source_dir, arxiv_id)
        (sources / (args.slug + ".json")).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        text = tex_text(source_dir)
        if text:
            (sources / (args.slug + ".md")).write_text(text, encoding="utf-8")
        found = copy_figures(source_dir, figures)
        (figures / "figures-manifest.md").write_text("# Figures Manifest\n\n" + "\n".join("- `%s`" % item for item in found) + "\n", encoding="utf-8")
        notes.append("source 成功，抽取 %d 个候选图片" % len(found))
    except Exception as exc:
        notes.append("source 失败：%s" % exc)
        metadata = {"arxiv_id": arxiv_id}
        found = []
    # source 失败时自动降级；显式 --html/--pdf 时保存对应副本。
    should_try_html = args.html or not source_ok
    if should_try_html:
        try:
            data = request_bytes("https://arxiv.org/html/" + arxiv_id, args.timeout)
            (sources / (args.slug + ".html")).write_bytes(data)
            html_ok = True
            notes.append("HTML 成功")
        except Exception as exc:
            notes.append("HTML 失败：%s" % exc)
    should_try_pdf = args.pdf or (not source_ok and not html_ok)
    if should_try_pdf:
        try:
            data = request_bytes("https://arxiv.org/pdf/" + arxiv_id, args.timeout)
            (sources / (args.slug + ".pdf")).write_bytes(data)
            pdf_ok = True
            notes.append("PDF 成功")
        except Exception as exc:
            notes.append("PDF 失败：%s" % exc)
    log = ["# Extraction Log", "", "- Generated: %s" % datetime.now(timezone.utc).isoformat(), "- Input: `%s`" % args.input, "- arXiv ID: `%s`" % arxiv_id, "", "## Sources", "", "| Source | Status |", "|---|---|", "| source tarball | %s |" % ("success" if source_ok else "failed"), "| HTML | %s |" % ("success" if html_ok else "not requested/failed"), "| PDF | %s |" % ("success" if pdf_ok else "not requested/failed"), "", "## Notes", ""] + ["- " + item for item in notes]
    log += ["", "## Candidate figures", ""] + ["- `%s`" % item for item in found]
    log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
    if not source_ok and not html_ok and not pdf_ok:
        print("所有来源均失败，详见", log_path, file=sys.stderr)
        return 2
    print("extracted:", workspace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
