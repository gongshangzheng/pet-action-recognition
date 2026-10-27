#!/usr/bin/env python3
"""Check that 文档引用 闭合：`《文档名》 §X.Y` 与 `[文](./x.md) §X.Y` 均指向存在的标题。

用法：
  python3 scripts/checks/check_doc_refs.py            # 检查，悬空即非零退出
  python3 scripts/checks/check_doc_refs.py --verbose   # 打印全部解析到的引用

范围（默认）：
  被引用目标 = management/docs/*.md、papers/docs/*.md
  扫描来源 = management/docs/*.md、papers/docs/*.md、openspec/changes/*/{proposal,design,tasks}.md
  （已归档 change 的历史记录不扫描：归档文本是历史证据，不随正文重编号改写）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_DIRS = [ROOT / "management/docs", ROOT / "papers/docs"]
LABEL = r"§\s*(\d+(?:\.\d+)?[a-z]?)"
REF_BY_NAME = re.compile(r"《([^》]+)》\s*" + LABEL)
REF_BY_LINK = re.compile(r"\]\(((?:\.\.?/)*[\w./-]+\.md)\)\s*" + LABEL)
HEADING_LABEL = re.compile(r"^#{1,6}\s*§\s*(\d+(?:\.\d+)?[a-z]?)")
FRONT_TITLE = re.compile(r"^title:\s*(.+)$", re.MULTILINE)
H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def title_of(path: Path) -> str:
    """文档名 = front matter title 的冒号前缀，缺省退回一级标题。"""
    text = path.read_text(encoding="utf-8")
    head = text[:2000]
    match = FRONT_TITLE.search(head) or H1.search(text)
    if not match:
        return path.stem
    return re.split(r"[：:]", match.group(1).strip())[0].strip()


def labels_of(path: Path) -> set[str]:
    """标题里出现的 §X / §X.Y / §X.Ya 编号集合。"""
    labels = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_LABEL.match(line)
        if match:
            labels.add(match.group(1))
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    docs: dict[str, Path] = {}
    for directory in DOC_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            docs[title_of(path)] = path

    sources = [p for d in DOC_DIRS if d.is_dir() for p in sorted(d.glob("*.md"))]
    changes = ROOT / "openspec/changes"
    sources += [p for p in sorted(changes.glob("*/*.md"))
                if p.parent.name != "archive" and p.name in {"proposal.md", "design.md", "tasks.md"}]

    dangling, resolved = [], 0
    by_path = {title_of(p): p for p in docs.values()}
    for source in sources:
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            for name, label in REF_BY_NAME.findall(line):
                target = docs.get(name)
                if target is None:
                    continue
                where = f"{source.relative_to(ROOT)}:{line_number}"
                if label in labels_of(target):
                    resolved += 1
                    if args.verbose:
                        print(f"OK   {where} 《{name}》 §{label}")
                else:
                    dangling.append((where, f"《{name}》 §{label}", str(target.relative_to(ROOT))))
            for link, label in REF_BY_LINK.findall(line):
                target = (source.parent / link).resolve()
                if not target.is_file():
                    dangling.append((f"{source.relative_to(ROOT)}:{line_number}",
                                     f"链接 {link}", "文件不存在"))
                    continue
                if label in labels_of(target):
                    resolved += 1
                else:
                    dangling.append((f"{source.relative_to(ROOT)}:{line_number}",
                                     f"{link} §{label}", str(target.relative_to(ROOT))))

    for where, ref, target in dangling:
        print(f"DANGLING {where} -> {ref}   ({target})")
    print(f"\n解析成功 {resolved} 条，悬空 {len(dangling)} 条（来源 {len(sources)} 个文件）")
    return 1 if dangling else 0


if __name__ == "__main__":
    raise SystemExit(main())
