#!/usr/bin/env python3
"""Recover the split cat-video tar into a verified, readable local dataset."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import uuid

from normalize_company_video_paths import (
    VideoIndex, compare_annotations, csv_bytes, json_bytes, normalize, read_csv,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "自作自偷"
OUTPUT = ROOT / "datasets" / "cat_raw"
PART_RE = re.compile(r"cat_raw\.tar\.part-(\d{3})$")
HASH_RE = re.compile(r"^([0-9a-fA-F]{64})  (.+)$")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))}
READ_SIZE = 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(READ_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_name(name: str) -> tuple[str, ...]:
    require(isinstance(name, str) and bool(name), "Empty archive filename")
    require("\\" not in name and not name.startswith("/")
            and not any(ord(c) < 32 for c in name), f"Unsafe archive name: {name!r}")
    pieces = name.rstrip("/").split("/")
    require(len(pieces) > 1 and pieces[0] in {"dataset-wyy", "annotation-wyy"},
            f"Unexpected archive root: {name!r}")
    for piece in pieces:
        require(piece not in {"", ".", ".."} and piece == piece.rstrip(" .")
                and ":" not in piece and piece.split(".", 1)[0].upper() not in WINDOWS_RESERVED,
                f"Windows-unsafe archive name: {name!r}")
    return tuple(pieces)


def load_expected(directory: Path) -> dict[str, tuple[int, str]]:
    sizes: dict[str, int] = {}
    hashes: dict[str, str] = {}
    with (directory / "source-sizes.tsv").open(encoding="utf-8", newline="") as handle:
        for line in handle:
            size, name = line.rstrip("\n").split("\t", 1)
            validate_name(name)
            require(name not in sizes and size.isdigit(), f"Invalid size entry: {name!r}")
            sizes[name] = int(size)
    with (directory / "source-files.sha256").open(encoding="utf-8", newline="") as handle:
        for line in handle:
            match = HASH_RE.fullmatch(line.rstrip("\n"))
            require(match is not None, "Invalid SHA-256 manifest line")
            digest, name = match.groups()
            validate_name(name)
            require(name not in hashes, f"Duplicate SHA-256 entry: {name!r}")
            hashes[name] = digest.lower()
    require(sizes.keys() == hashes.keys(), "Size/SHA-256 manifest file sets differ")
    require(bool(sizes), "Empty source manifest")
    return {name: (size, hashes[name]) for name, size in sizes.items()}


def find_parts(directory: Path) -> list[Path]:
    parts = sorted(p for p in directory.iterdir() if PART_RE.fullmatch(p.name))
    require(parts and [p.name for p in parts] ==
            [f"cat_raw.tar.part-{i:03d}" for i in range(len(parts))],
            "Missing, duplicate, or nonconsecutive archive part")
    part_size = parts[0].stat().st_size
    require(part_size > 0 and all(p.stat().st_size == part_size for p in parts[:-1]),
            "Non-final part sizes differ")
    require(0 < parts[-1].stat().st_size <= part_size, "Invalid final part size")
    return parts


class PartReader:
    """Read numbered parts as one stream while computing their individual hashes."""

    def __init__(self, parts: list[Path]):
        self.parts = parts
        self.index = 0
        self.current = None
        self.digest = hashlib.sha256()
        self.hashes: dict[str, str] = {}
        self.total = 0

    def read(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        if size < 0:
            size = READ_SIZE
        chunks = []
        remaining = size
        while remaining and self.index < len(self.parts):
            if self.current is None:
                self.current = self.parts[self.index].open("rb")
            block = self.current.read(remaining)
            if block:
                self.digest.update(block)
                self.total += len(block)
                chunks.append(block)
                remaining -= len(block)
                continue
            self.current.close()
            self.current = None
            self.hashes[self.parts[self.index].name] = self.digest.hexdigest()
            self.digest = hashlib.sha256()
            self.index += 1
        return b"".join(chunks)

    def drain(self) -> None:
        while self.read(READ_SIZE):
            pass

    def close(self) -> None:
        if self.current is not None:
            self.current.close()
            self.current = None


def target_for(name: str, first_bytes: bytes) -> tuple[Path, str]:
    pieces = validate_name(name)
    basename = pieces[-1]
    if pieces[0] == "dataset-wyy" and basename.lower().endswith(".mp4") and not basename.startswith("._"):
        return Path("videos", *pieces[1:]), "video"
    if name in {"annotation-wyy/merged_annotations.csv", "annotation-wyy/merged_annotations.json"}:
        return Path("annotations", "original", basename), "original_annotation"
    if (basename.startswith("._") and first_bytes.startswith(b"\x00\x05\x16\x07")) or (
        basename == ".DS_Store" and first_bytes.startswith(b"\x00\x00\x00\x01Bud1")
    ):
        return Path("provenance", "apple_metadata", *pieces), "apple_metadata"
    return Path("provenance", "other_files", *pieces), "other_file"


def inspect_archive(parts: list[Path], expected: dict[str, tuple[int, str]],
                    destination: Path | None = None) -> tuple[list[dict], dict[str, str]]:
    reader = PartReader(parts)
    records = []
    seen = set()
    target_names = set()
    directories = set()
    try:
        with tarfile.open(fileobj=reader, mode="r|", encoding="utf-8", errors="strict") as archive:
            for member in archive:
                if member.isdir():
                    # The two root directory headers are expected; nested directories are permitted.
                    clean = member.name.rstrip("/")
                    if clean not in {"dataset-wyy", "annotation-wyy"}:
                        validate_name(clean)
                    directories.add(clean)
                    continue
                require(member.isfile() and not getattr(member, "sparse", None),
                        f"Link or unsupported archive member: {member.name!r}")
                name = member.name
                validate_name(name)
                require(name in expected and name not in seen, f"Unexpected/duplicate archive file: {name!r}")
                require(member.size == expected[name][0], f"Archive size mismatch: {name!r}")
                source = archive.extractfile(member)
                require(source is not None, f"Unreadable archive member: {name!r}")
                first = source.read(min(8, member.size))
                relative, kind = target_for(name, first)
                folded = relative.as_posix().casefold()
                require(folded not in target_names, f"Windows filename collision: {relative}")
                target_names.add(folded)
                digest = hashlib.sha256()
                digest.update(first)
                copied = len(first)
                output = None
                if destination is not None:
                    path = destination / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    output = path.open("xb")
                    output.write(first)
                try:
                    while True:
                        block = source.read(READ_SIZE)
                        if not block:
                            break
                        digest.update(block)
                        copied += len(block)
                        if output is not None:
                            output.write(block)
                finally:
                    if output is not None:
                        output.close()
                require(copied == member.size and digest.hexdigest() == expected[name][1],
                        f"Source SHA-256/length mismatch: {name!r}")
                seen.add(name)
                records.append(dict(source=name, destination=relative.as_posix(), kind=kind,
                                    bytes=member.size, sha256=digest.hexdigest()))
        reader.drain()
        require(seen == expected.keys(), f"Archive missing {len(expected.keys() - seen)} source files")
        require(reader.total == sum(p.stat().st_size for p in parts), "Archive part changed while reading")
        return records, reader.hashes
    finally:
        reader.close()


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value) -> None:
    path.write_bytes(json_bytes(value))


def annotation_indexes(stage: Path, published: Path) -> dict:
    annotation_dir = stage / "annotations"
    csv_source = annotation_dir / "original" / "merged_annotations.csv"
    json_source = annotation_dir / "original" / "merged_annotations.json"
    fields, original_rows = read_csv(csv_source.read_bytes())
    original_tasks = json.loads(json_source.read_text(encoding="utf-8-sig"))
    require(isinstance(original_tasks, list), "Original JSON is not a task list")
    video_index = VideoIndex.scan(stage / "videos")
    absolute_rows, absolute_tasks, mappings, methods, common = normalize(
        original_rows, original_tasks, video_index)
    stage_video_prefix = str(stage / "videos") + os.sep
    final_video_prefix = str(published / "videos") + os.sep
    for row in absolute_rows:
        require(row["video"].startswith(stage_video_prefix), "Mapped CSV path escapes videos")
        row["video"] = final_video_prefix + row["video"][len(stage_video_prefix):]
    for task in absolute_tasks:
        old = task["data"]["video"]
        require(old.startswith(stage_video_prefix), "Mapped JSON path escapes videos")
        task["data"]["video"] = final_video_prefix + old[len(stage_video_prefix):]
    compare_annotations(fields, original_rows, original_tasks,
                        fields, absolute_rows, absolute_tasks, absolute_rows, absolute_tasks)
    relative_rows = [dict(row, video="videos/" + Path(row["video"]).name)
                     for row in absolute_rows]
    relative_tasks = []
    for task in absolute_tasks:
        converted = dict(task)
        converted["data"] = dict(task["data"], video="videos/" + Path(task["data"]["video"]).name)
        relative_tasks.append(converted)
    compare_annotations(fields, original_rows, original_tasks,
                        fields, relative_rows, relative_tasks, relative_rows, relative_tasks)
    for name, rows in (("merged_annotations.local.csv", absolute_rows),
                       ("merged_annotations.relative.csv", relative_rows)):
        (annotation_dir / name).write_bytes(csv_bytes(fields, rows))
    write_json(annotation_dir / "merged_annotations.local.json", absolute_tasks)
    write_json(annotation_dir / "merged_annotations.relative.json", relative_tasks)
    for name, rows, tasks in (("local", absolute_rows, absolute_tasks),
                              ("relative", relative_rows, relative_tasks)):
        check_fields, check_rows = read_csv((annotation_dir / f"merged_annotations.{name}.csv").read_bytes())
        check_tasks = json.loads((annotation_dir / f"merged_annotations.{name}.json").read_text(encoding="utf-8"))
        compare_annotations(fields, original_rows, original_tasks,
                            check_fields, check_rows, check_tasks, rows, tasks)

    interval_fields = ["video", "task_id", "annotation_id", "result_id", "range_index",
                       "label_index", "start_frame", "end_frame", "label"]
    intervals = []
    task_rows = []
    by_video = defaultdict(list)
    for task in relative_tasks:
        video = task["data"]["video"]
        by_video[video].append(task)
        for annotation in task.get("annotations") or []:
            if annotation.get("was_cancelled"):
                continue
            for result in annotation.get("result") or []:
                if result.get("type") != "timelinelabels":
                    continue
                value = result.get("value") or {}
                for range_index, span in enumerate(value.get("ranges") or []):
                    start, end = span.get("start"), span.get("end")
                    require(isinstance(start, int) and not isinstance(start, bool)
                            and isinstance(end, int) and not isinstance(end, bool)
                            and 1 <= start <= end,
                            f"Invalid frame interval in task {task.get('id')}")
                    for label_index, label in enumerate(value.get("timelinelabels") or []):
                        require(isinstance(label, str) and bool(label), "Invalid interval label")
                        intervals.append(dict(video=video, task_id=task.get("id"),
                                              annotation_id=annotation.get("id"),
                                              result_id=result.get("id"), range_index=range_index,
                                              label_index=label_index, start_frame=start,
                                              end_frame=end, label=label))
    write_csv(annotation_dir / "intervals.csv", interval_fields, intervals)
    label_counts = Counter(row["label"] for row in intervals)
    label_videos = defaultdict(set)
    for row in intervals:
        label_videos[row["label"]].add(row["video"])
    class_rows = [dict(label=label, interval_count=label_counts[label],
                       videos=len(label_videos[label])) for label in sorted(label_counts)]
    write_csv(annotation_dir / "classes.csv", ["label", "interval_count", "videos"], class_rows)
    for video in sorted(video_index.names):
        relative = "videos/" + video
        tasks = by_video.get(relative, [])
        task_rows.append(dict(video=relative,
                              bytes=(stage / relative).stat().st_size,
                              task_ids=";".join(str(task.get("id", "")) for task in tasks),
                              task_count=len(tasks),
                              cancelled_annotations=sum(bool(ann.get("was_cancelled"))
                                                        for task in tasks for ann in task.get("annotations") or []),
                              interval_count=sum(row["video"] == relative for row in intervals)))
    write_csv(annotation_dir / "videos.csv",
              ["video", "bytes", "task_ids", "task_count", "cancelled_annotations", "interval_count"],
              task_rows)
    mapping_rows = []
    for mapping in mappings:
        path = Path(mapping["local_video"])
        mapping_rows.append(dict(source=mapping["source"], record_index=mapping["record_index"],
                                 task_id=mapping["task_id"], original_video=mapping["original_video"],
                                 video="videos/" + path.name, method=mapping["method"]))
    write_csv(annotation_dir / "path_mapping.csv",
              ["source", "record_index", "task_id", "original_video", "video", "method"],
              mapping_rows)
    summary = dict(csv_rows=len(original_rows), json_tasks=len(original_tasks),
                   unique_videos=len(video_index.names), intervals=len(intervals),
                   observed_classes=len(class_rows), mapping_methods=methods,
                   common_task_ids=common, classes=class_rows)
    write_json(annotation_dir / "summary.json", summary)
    return dict(summary=summary, videos=task_rows, intervals=intervals)


def make_viewer(stage: Path, model: dict) -> None:
    template = (ROOT / "scripts" / "templates" / "cat_dataset_index.html").read_text(encoding="utf-8")
    payload = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    require(template.count("__DATA_JSON__") == 1, "Invalid viewer template")
    (stage / "index.html").write_text(template.replace("__DATA_JSON__", payload), encoding="utf-8")


def make_readme(stage: Path, summary: dict, report: dict) -> None:
    content = f"""# 猫行为原始数据（已校验恢复）

恢复时间：{report['completed_at']}。视频 {summary['unique_videos']} 条，原始 JSON task
{summary['json_tasks']} 个，原始 CSV {summary['csv_rows']} 行，动作区间-标签记录
{summary['intervals']} 条，观察到 {summary['observed_classes']} 个类别。

直接打开 `index.html` 可搜索视频和查看原动作帧区间；原视频位于 `videos/`。
原视频编码保持不变，浏览器若不支持 H.265/HEVC，可用本地视频播放器打开文件。

`annotations/original/` 是字节不变的 Label Studio CSV/JSON。
`annotations/merged_annotations.local.*` 仅把视频地址改为本机绝对路径；
`annotations/merged_annotations.relative.*` 仅改为相对当前数据集根目录的路径。
`annotations/intervals.csv` 一行对应一个原始 range 与一个标签，保留 task、
annotation、result 及范围索引，重叠区间和重复记录不合并。
`annotations/videos.csv` 包含所有视频，包括未标注或取消标注的任务；
空区间不表示“无动作/无猫”。`classes.csv` 和 `summary.json` 是浏览统计。
`annotations/path_mapping.csv` 保留原 Label Studio 引用与本机视频的对应关系。

`provenance/apple_metadata/` 保存 macOS `._*` 和 `.DS_Store` 伴随文件，
不作为视频样本。`manifests/` 存放逐文件 SHA-256 验证报告和分卷哈希。
原始分卷保留在 `E:\\pet-final\\自作自偷`，此处未复制约 10 GB 归档。

训练接入：这是带帧区间、可能重叠的监督数据。后续可使用 `intervals.csv` 构建
短窗或时序读取器；默认 MMAction2 VideoDataset 的“整视频路径 + 单个整数类别”
格式不能直接表达这些区间。帧号基数和端点语义仍需与标注模板核对；未切片、
未决定类别、未划分训练/验证集，也未为未标注帧生成负标签。

逐文件源哈希全部一致：{report['verified_files']}/{report['source_files']}。
"""
    (stage / "README.md").write_text(content, encoding="utf-8")


def run(source: Path, output: Path) -> dict:
    source = source.resolve(strict=True)
    output = output.resolve(strict=False)
    require(output == OUTPUT.resolve(strict=False), "Output must be datasets/cat_raw")
    require(not output.exists() and not output.is_symlink(), "Output already exists; refusing overwrite")
    expected = load_expected(source)
    parts = find_parts(source)
    part_stats = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in parts}
    bytes_needed = sum(size for size, _ in expected.values())
    disk_free = shutil.disk_usage(ROOT).free
    require(disk_free >= bytes_needed + 2 * 1024**3,
            f"Insufficient free disk space: need {bytes_needed + 2 * 1024**3}, have {disk_free}")
    print(f"PREFLIGHT parts={len(parts)} source_files={len(expected)} bytes={bytes_needed}", flush=True)
    checked, part_hashes = inspect_archive(parts, expected)
    print(f"PREFLIGHT_PASS members={len(checked)} source_sha256=all", flush=True)
    stage = output.parent / f".cat_raw_recovery_{uuid.uuid4().hex[:12]}"
    stage.mkdir(parents=True, exist_ok=False)
    try:
        extracted, second_part_hashes = inspect_archive(parts, expected, stage)
        require(checked == extracted and part_hashes == second_part_hashes,
                "Archive changed between inspection and extraction")
        require({p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in parts} == part_stats,
                "Input part changed during recovery")
        for index, record in enumerate(extracted, 1):
            path = stage / record["destination"]
            require(path.stat().st_size == record["bytes"]
                    and sha256_file(path) == record["sha256"],
                    f"Extracted file differs: {record['source']}")
            if index % 500 == 0:
                print(f"VERIFY {index}/{len(extracted)}", flush=True)
        indexed = annotation_indexes(stage, output)
        manifest_dir = stage / "manifests"
        manifest_dir.mkdir()
        with (manifest_dir / "source_manifest.jsonl").open("x", encoding="utf-8", newline="") as handle:
            for record in extracted:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        with (manifest_dir / "parts_512.local.sha256").open("x", encoding="utf-8", newline="") as handle:
            for part in parts:
                handle.write(f"{part_hashes[part.name]}  {part.name}\n")
        old_manifest = source / "parts.sha256"
        if old_manifest.exists():
            shutil.copyfile(old_manifest, manifest_dir / "parts_128.old.sha256")
        report = dict(schema="cat-raw-recovery-v1", completed_at=datetime.now(timezone.utc).isoformat(),
                      source_files=len(expected), verified_files=len(extracted),
                      source_bytes=bytes_needed, archive_parts=len(parts),
                      archive_bytes=sum(p.stat().st_size for p in parts),
                      normal_videos=sum(record["kind"] == "video" for record in extracted),
                      original_annotations=sum(record["kind"] == "original_annotation" for record in extracted),
                      preserved_metadata=sum(record["kind"] in {"apple_metadata", "other_file"} for record in extracted),
                      parts_sha256=part_hashes, annotation_summary=indexed["summary"],
                      original_source_unchanged=True, video_decoded=False,
                      training_started=False, frame_interpretation="original frame numbers; convention not verified")
        make_viewer(stage, indexed)
        make_readme(stage, indexed["summary"], report)
        write_json(manifest_dir / "verification.json", report)
        require(not output.exists(), "Output appeared while preparing the dataset")
        stage.rename(output)
        print("CAT_RAW_RECOVERY_DONE " + json.dumps({
            "destination": str(output), "videos": report["normal_videos"],
            "source_files_verified": report["verified_files"],
            "intervals": indexed["summary"]["intervals"]}, ensure_ascii=False), flush=True)
        return report
    except Exception:
        print(f"INCOMPLETE_STAGE {stage}", file=sys.stderr, flush=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        run(args.source, args.output)
        return 0
    except (OSError, ValueError, tarfile.TarError, json.JSONDecodeError) as exc:
        print(f"CAT_RAW_RECOVERY_FAILED {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
