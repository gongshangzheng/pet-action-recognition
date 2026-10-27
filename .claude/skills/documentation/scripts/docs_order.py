#!/usr/bin/env python3
"""查看、插入和重排 Markdown 文档的 frontmatter ``order`` 字段。

排序键与 server/routers/management.py 的 _doc_sort_key 同源
（目录内四级：order → id → date 降序 → slug；顶层文件夹优先级由单目录输入天然固定）。
后端排序链若变更，本脚本需同步，否则插入位置会与页面顺序不一致。

用法：
    python3 .agents/skills/documentation/scripts/docs_order.py list management/docs/数字人概述
    python3 .agents/skills/documentation/scripts/docs_order.py insert management/docs/数字人概述 \
        --title "数字人领域问题" --after 数字人介绍与技术路线 --create --apply
    python3 .agents/skills/documentation/scripts/docs_order.py renumber management/docs/数字人概述 --apply

所有会修改文件的命令默认只输出计划；只有传入 ``--apply`` 才会写盘。
脚本只使用 Python 标准库，并且只编辑 YAML frontmatter 中的 ``order:`` 行。
"""
import argparse
import datetime as dt
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ORDER_RE = re.compile(r"^(?P<prefix>\s*order\s*:\s*)(?P<value>.*?)(?P<ending>\r?\n?)$")
FIELD_RE = re.compile(r"^\s*(?P<key>[A-Za-z_][\w-]*)\s*:\s*(?P<value>.*?)\s*(?:#.*)?(?:\r?\n)?$")


class OrderError(Exception):
    """用户输入或文档 frontmatter 不符合本工具约束。"""


@dataclass
class Document:
    """一篇 Markdown 文档及其排序所需的最少元数据。"""

    path: Path
    slug: str
    title: str
    order: Optional[float]
    raw_order: Optional[str]
    identifier: Optional[float]
    date: str
    text: str


@dataclass
class PlannedChange:
    """一个文件的新 order 或新建文件的内容。"""

    path: Path
    order: int
    created: bool = False
    content: Optional[str] = None


def _frontmatter_lines(text: str) -> Tuple[List[str], int]:
    """返回 frontmatter 行及其结束行索引；没有合法块时抛出异常。"""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise OrderError("缺少以 --- 开始的 frontmatter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines, index
    raise OrderError("frontmatter 缺少结束的 ---")


def _unquote(value: str) -> str:
    """读取普通 YAML 标量；这里只需覆盖 title、date 和数值字段。"""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _number(value: Optional[str]) -> Optional[float]:
    """将 order/id 的数值转换为 float，非数值与布尔值视为缺失。"""
    if value is None:
        return None
    candidate = _unquote(value).split("#", 1)[0].strip()
    if not candidate or candidate.lower() in {"true", "false", "null", "none", "~"}:
        return None
    try:
        parsed = float(candidate)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _metadata(lines: Sequence[str], end: int) -> Dict[str, str]:
    """读取行级 frontmatter 字段，不改写其他 YAML 表达形式。"""
    values: Dict[str, str] = {}
    for line in lines[1:end]:
        match = FIELD_RE.match(line)
        if match:
            values[match.group("key")] = match.group("value").strip()
    return values


def _order_lines(lines: Sequence[str], end: int) -> List[int]:
    """找出 frontmatter 中全部 order 行，用于拒绝不确定的编辑。"""
    return [index for index in range(1, end) if ORDER_RE.match(lines[index])]


def _date_ordinal(value: str) -> int:
    """与 management.py 的日期降序排序保持一致。"""
    try:
        return dt.date.fromisoformat(value[:10]).toordinal()
    except ValueError:
        return 0


def _sort_number(value: Optional[float]) -> float:
    return float("inf") if value is None else value


def _sort_key(document: Document) -> Tuple[float, float, int, str]:
    """与 server/routers/management.py:_doc_sort_key 的目录内链路同源。

    顶层文件夹优先级已由本工具的单目录输入固定，故这里只实现
    ``order → id → date 降序 → slug`` 四级。
    """
    return (
        _sort_number(document.order),
        _sort_number(document.identifier),
        -_date_ordinal(document.date),
        document.slug,
    )


def _read_document(root: Path, path: Path) -> Document:
    """读取单篇文档，并解析排序元数据。"""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise OrderError("不是 UTF-8 文本") from error
    lines, end = _frontmatter_lines(text)
    positions = _order_lines(lines, end)
    if len(positions) > 1:
        raise OrderError("frontmatter 含多个 order: 行")
    fields = _metadata(lines, end)
    raw_order = None
    if positions:
        match = ORDER_RE.match(lines[positions[0]])
        raw_order = match.group("value") if match else None
    slug = path.relative_to(root).with_suffix("").as_posix()
    return Document(
        path=path,
        slug=slug,
        title=_unquote(fields.get("title", slug)),
        order=_number(raw_order),
        raw_order=raw_order,
        identifier=_number(fields.get("id")),
        date=_unquote(fields.get("date", "")),
        text=text,
    )


def load_documents(directory: Path) -> List[Document]:
    """递归读取目录下的 Markdown 文档，跳过下划线资产目录。"""
    if not directory.is_dir():
        raise OrderError("目录不存在或不是目录: {0}".format(directory))
    documents: List[Document] = []
    for path in sorted(directory.rglob("*.md")):
        if any(part.startswith("_") for part in path.relative_to(directory).parts):
            continue
        try:
            documents.append(_read_document(directory, path))
        except OrderError as error:
            raise OrderError("{0}: {1}".format(path, error)) from error
    return sorted(documents, key=_sort_key)


def duplicate_orders(documents: Iterable[Document]) -> Dict[float, List[Document]]:
    """找出真实数字值重复的 order；未写或非数字值不算重复。"""
    grouped: Dict[float, List[Document]] = {}
    for document in documents:
        if document.order is not None:
            grouped.setdefault(document.order, []).append(document)
    return {value: group for value, group in grouped.items() if len(group) > 1}


def _format_order(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return str(int(value)) if value.is_integer() else str(value)


def _print_duplicates(duplicates: Dict[float, List[Document]]) -> None:
    for value, group in sorted(duplicates.items()):
        print(
            "DUPLICATE order {0}: {1}".format(
                _format_order(value), ", ".join(document.slug for document in group)
            ),
            file=sys.stderr,
        )


def _print_list(documents: Sequence[Document]) -> None:
    print("order\ttitle\tslug")
    for document in documents:
        print("{0}\t{1}\t{2}".format(_format_order(document.order), document.title, document.slug))

    numeric = [document for document in documents if document.order is not None]
    print("\n相邻空位：")
    if len(numeric) < 2:
        print("  （不足两篇带数字 order 的文档）")
    else:
        for left, right in zip(numeric, numeric[1:]):
            if left.order is None or right.order is None:
                continue
            gap = max(0, int(math.ceil(right.order) - math.floor(left.order) - 1))
            slot = "可插入" if gap else "无空位"
            print(
                "  {0} → {1}: {2} 个整数空位（{3}）".format(
                    left.slug, right.slug, gap, slot
                )
            )


def _replace_order(text: str, order: int) -> str:
    """仅更新 order 行；没有该字段时插到 title 之后。"""
    lines, end = _frontmatter_lines(text)
    positions = _order_lines(lines, end)
    if len(positions) > 1:
        raise OrderError("frontmatter 含多个 order: 行")
    if positions:
        index = positions[0]
        match = ORDER_RE.match(lines[index])
        if not match:
            raise OrderError("无法解析 order: 行")
        value = match.group("value")
        comment = ""
        if "#" in value:
            comment = " #" + value.split("#", 1)[1].rstrip("\r\n")
        lines[index] = "{0}{1}{2}{3}".format(
            match.group("prefix"), order, comment, match.group("ending") or "\n"
        )
    else:
        insert_at = end
        for index in range(1, end):
            field = FIELD_RE.match(lines[index])
            if field and field.group("key") == "title":
                insert_at = index + 1
                break
        lines.insert(insert_at, "order: {0}\n".format(order))
    return "".join(lines)


def _validate_written_frontmatter(text: str) -> None:
    """校验本工具的写入结果，不依赖第三方 YAML 解析器。"""
    lines, end = _frontmatter_lines(text)
    positions = _order_lines(lines, end)
    if len(positions) != 1:
        raise OrderError("写入后 frontmatter 必须且只能有一个 order: 行")
    match = ORDER_RE.match(lines[positions[0]])
    if not match or _number(match.group("value")) is None:
        raise OrderError("写入后 order: 必须为有限数字")


def _planned_text(change: PlannedChange) -> str:
    if change.content is not None:
        return change.content
    original = change.path.read_text(encoding="utf-8")
    return _replace_order(original, change.order)


def _show_plan(changes: Sequence[PlannedChange]) -> None:
    if not changes:
        print("无改动。")
        return
    for change in changes:
        if change.created:
            print("CREATE {0} (order: {1})".format(change.path, change.order))
            continue
        document = _read_document(change.path.parent, change.path)
        print("UPDATE {0}: {1} → {2}".format(
            change.path, _format_order(document.order), change.order
        ))


def _apply_changes(changes: Sequence[PlannedChange]) -> None:
    """逐文件写入并验证；某文件验证失败时仅回滚该文件。"""
    for change in changes:
        existed = change.path.exists()
        old_content = change.path.read_text(encoding="utf-8") if existed else None
        new_content = _planned_text(change)
        change.path.parent.mkdir(parents=True, exist_ok=True)
        change.path.write_text(new_content, encoding="utf-8")
        try:
            _validate_written_frontmatter(new_content)
        except OrderError:
            if existed and old_content is not None:
                change.path.write_text(old_content, encoding="utf-8")
            else:
                change.path.unlink(missing_ok=True)
            raise


def _check_duplicates(documents: Sequence[Document], force: bool) -> None:
    duplicates = duplicate_orders(documents)
    if duplicates and not force:
        _print_duplicates(duplicates)
        raise OrderError("存在重复 order；请先修复，或显式传入 --force")


def _find_reference(documents: Sequence[Document], value: str) -> int:
    """按 slug 优先、title 次之定位唯一文档。"""
    matches = [index for index, document in enumerate(documents) if document.slug == value]
    if not matches:
        matches = [index for index, document in enumerate(documents) if document.title == value]
    if not matches:
        raise OrderError("找不到位置参考文档: {0}".format(value))
    if len(matches) > 1:
        raise OrderError("位置参考不唯一，请改用 slug: {0}".format(value))
    return matches[0]


def _position_from_args(documents: Sequence[Document], args: argparse.Namespace) -> int:
    if args.after:
        return _find_reference(documents, args.after) + 1
    if args.before:
        return _find_reference(documents, args.before)
    if args.index is not None:
        if args.index < 0 or args.index > len(documents):
            raise OrderError("--index 必须在 0 到 {0} 之间".format(len(documents)))
        return args.index
    return len(documents)


def _insertion_order(documents: Sequence[Document], position: int) -> Optional[int]:
    """有明确整数空位时返回中点；没有则返回 None 以触发重排。"""
    previous = documents[position - 1] if position > 0 else None
    following = documents[position] if position < len(documents) else None
    if previous is None and following is None:
        return 10
    if previous is None:
        if following is not None and following.order is not None and following.order.is_integer():
            return int(following.order) - 10
        return None
    if following is None:
        if previous.order is not None and previous.order.is_integer():
            return int(previous.order) + 10
        return None
    if (
        previous.order is None
        or following.order is None
        or not previous.order.is_integer()
        or not following.order.is_integer()
    ):
        return None
    low, high = int(previous.order), int(following.order)
    if high - low <= 1:
        return None
    return low + (high - low) // 2


def _new_document(path: Path, title: str, author: str, order: int) -> str:
    today = dt.date.today().isoformat()
    return (
        "---\n"
        "title: {0}\n"
        "author: {1}\n"
        "date: {2}\n"
        "tags: []\n"
        "order: {3}\n"
        "summary:\n"
        "---\n\n"
        "# {0}\n\n"
        "<!-- 在此补充正文。 -->\n"
    ).format(title, author, today, order)


def command_list(args: argparse.Namespace) -> int:
    documents = load_documents(args.directory)
    _print_list(documents)
    duplicates = duplicate_orders(documents)
    if duplicates:
        _print_duplicates(duplicates)
        return 2
    return 0


def command_renumber(args: argparse.Namespace) -> int:
    documents = load_documents(args.directory)
    _check_duplicates(documents, args.force)
    if args.step <= 0:
        raise OrderError("--step 必须是正整数")
    changes = [
        PlannedChange(document.path, args.start + index * args.step)
        for index, document in enumerate(documents)
        if document.order != args.start + index * args.step
    ]
    _show_plan(changes)
    if args.apply:
        _apply_changes(changes)
    else:
        print("DRY-RUN：传入 --apply 才会写盘。")
    return 0


def command_insert(args: argparse.Namespace) -> int:
    documents = load_documents(args.directory)
    _check_duplicates(documents, args.force)
    slug = args.slug or args.title
    if not slug or slug.startswith("/") or ".." in Path(slug).parts:
        raise OrderError("--slug 必须是目录内的安全相对路径")
    target = args.directory / (slug if slug.endswith(".md") else slug + ".md")
    if target.exists():
        raise OrderError("目标文档已存在；insert 仅用于新建文档: {0}".format(target))
    if not args.create:
        raise OrderError("目标文档不存在；请传入 --create")

    if args.order is not None:
        if args.order != int(args.order):
            raise OrderError("--order 必须是整数")
        order = int(args.order)
        if any(document.order == order for document in documents) and not args.force:
            raise OrderError("order {0} 已被使用；请改用空位或显式传入 --force".format(order))
        changes = [PlannedChange(target, order, True, _new_document(target, args.title, args.author, order))]
    else:
        position = _position_from_args(documents, args)
        order = None if args.shift else _insertion_order(documents, position)
        if order is not None:
            changes = [PlannedChange(target, order, True, _new_document(target, args.title, args.author, order))]
        else:
            # 无整数空位时只位移插入点及其后文档：前序 order 不应因插入而改动。
            previous = documents[position - 1] if position > 0 else None
            following = documents[position] if position < len(documents) else None
            if previous is not None and previous.order is not None and previous.order.is_integer():
                first_order = int(previous.order) + 10
            elif following is not None and following.order is not None and following.order.is_integer():
                first_order = int(following.order) - 10
            else:
                # 周边没有可作为局部基准的整数 order，只能规范化整个目录。
                position = 0
                first_order = 10
            all_paths = list(documents[position:])
            all_paths.insert(0, Document(target, slug, args.title, None, None, None, "", ""))
            changes = []
            for index, document in enumerate(all_paths):
                assigned = first_order + index * 10
                if document.path == target:
                    changes.append(
                        PlannedChange(target, assigned, True, _new_document(target, args.title, args.author, assigned))
                    )
                elif document.order != assigned:
                    changes.append(PlannedChange(document.path, assigned))
    _show_plan(changes)
    if args.apply:
        _apply_changes(changes)
    else:
        print("DRY-RUN：传入 --apply 才会写盘。")
    return 0


def _directory(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器。"""
    parser = argparse.ArgumentParser(description="查看、插入和重排文档 frontmatter 的 order 字段")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出排序、空位与重复值")
    list_parser.add_argument("directory", type=_directory, help="文档目录")
    list_parser.set_defaults(handler=command_list)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("directory", type=_directory, help="文档目录")
    common.add_argument("--apply", action="store_true", help="将计划写入文件（默认 dry-run）")
    common.add_argument("--force", action="store_true", help="重复 order 存在时仍允许写入")

    insert_parser = subparsers.add_parser("insert", parents=[common], help="插入一篇新文档")
    insert_parser.add_argument("--title", required=True, help="新文档标题")
    insert_parser.add_argument("--slug", help="新文档 slug/文件名，默认使用 title")
    insert_parser.add_argument("--author", required=True, help="新文档作者（frontmatter 必填项，工具不替你编造）")
    insert_parser.add_argument("--create", action="store_true", help="创建不存在的新文档")
    placement = insert_parser.add_mutually_exclusive_group()
    placement.add_argument("--after", help="排在指定 slug 或 title 之后")
    placement.add_argument("--before", help="排在指定 slug 或 title 之前")
    placement.add_argument("--index", type=int, help="插入位置（从 0 开始）")
    placement.add_argument("--order", type=float, help="直接指定 order 整数")
    insert_parser.add_argument("--shift", action="store_true", help="即使有空位也重排后续顺序")
    insert_parser.set_defaults(handler=command_insert)

    renumber_parser = subparsers.add_parser("renumber", parents=[common], help="按当前顺序整体重排")
    renumber_parser.add_argument("--step", type=int, default=10, help="编号步长（默认：10）")
    renumber_parser.add_argument("--start", type=int, default=10, help="起始编号（默认：10）")
    renumber_parser.set_defaults(handler=command_renumber)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口，返回适合 shell 使用的退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except OrderError as error:
        print("ERROR: {0}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
