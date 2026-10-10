#!/usr/bin/env python3
"""Normalize only Label Studio video addresses; leave source annotations untouched."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit
import uuid


class MappingError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise MappingError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames
    require(fields and "video" in fields, "CSV must have a video column")
    require(len(fields) == len(set(fields)), "Duplicate CSV column names")
    rows = list(reader)
    require(all(set(row) == set(fields) and all(v is not None for v in row.values())
                for row in rows), "Malformed CSV row")
    return fields, rows


def csv_bytes(fields, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


@dataclass
class VideoIndex:
    root: Path
    names: dict
    stats: dict
    appledouble: int = 0

    @classmethod
    def scan(cls, root):
        root = root.resolve(strict=True)
        require(root.is_dir(), "Video root is not a directory")
        names, stats, appledouble = defaultdict(list), {}, 0
        for entry in sorted(root.rglob("*")):
            if entry.name.startswith("._"):
                appledouble += int(entry.is_file())
                continue
            if not entry.is_file() or entry.suffix.lower() != ".mp4":
                continue
            path = entry.resolve(strict=True)
            require(root in path.parents, "Video symlink escapes the video root")
            names[entry.name].append(path)
            stat = path.stat()
            stats[path] = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
        require(bool(names), "No normal MP4 videos found")
        return cls(root, dict(names), stats, appledouble)

    def lookup(self, name, method):
        require(name and not name.startswith("._"), "Invalid video filename")
        candidates = self.names.get(name, [])
        require(len(candidates) == 1,
                f"Video filename has {len(candidates)} exact matches: {name}")
        return str(candidates[0]), method

    def resolve(self, reference):
        require(isinstance(reference, str) and bool(reference), "Empty/non-string video address")
        require(not any(ord(c) < 32 for c in reference), "Control character in video address")
        if reference.startswith(str(self.root) + "/"):
            path = Path(reference).resolve()
            require(self.root in path.parents, "Local video address escapes the video root")
            known = {candidate for values in self.names.values() for candidate in values}
            require(path in known, "Local video address is not an indexed normal video")
            return str(path), "absolute"
        parsed = urlsplit(reference)
        require(parsed.scheme in ("", "http", "https"), "Unsupported video address scheme")
        if parsed.path.rstrip("/") == "/data/local-files":
            values = parse_qs(parsed.query, keep_blank_values=True).get("d", [])
            require(len(values) == 1 and bool(values[0]), "local-files requires one nonempty d parameter")
            # parse_qs already decoded d; decoding a second time changes literal percent filenames.
            return self.lookup(PurePosixPath(values[0]).name, "local_files")
        if parsed.path.startswith("/data/upload/"):
            name = PurePosixPath(unquote(parsed.path)).name
            if name in self.names:
                return self.lookup(name, "upload_exact")
            stripped = re.sub(r"^[0-9a-fA-F]{8}-", "", name, count=1)
            require(stripped != name, "Upload address has no matching filename or recognized prefix")
            return self.lookup(stripped, "upload_prefix_removed")
        raise MappingError("Unsupported video address format")


def task_video(task):
    require(isinstance(task, dict) and isinstance(task.get("data"), dict)
            and "video" in task["data"], "JSON task must have data.video")
    return task["data"]["video"]


def json_without_video(task):
    result = dict(task)
    result["data"] = {key: value for key, value in task["data"].items() if key != "video"}
    # Serialization also distinguishes JSON number/bool types during comparison.
    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize(rows, tasks, index):
    require(isinstance(tasks, list), "JSON annotations must be a task list")
    local_rows, local_tasks, mappings = [], [], []
    methods = Counter()
    by_id = {"csv": defaultdict(set), "json": defaultdict(set)}
    for source, records in (("csv", rows), ("json", tasks)):
        for number, record in enumerate(records, 1):
            reference = record["video"] if source == "csv" else task_video(record)
            try:
                path, method = index.resolve(reference)
            except (MappingError, ValueError) as exc:
                raise MappingError(f"{source} record {number}: {exc}") from exc
            task_id = record.get("id", "")
            if task_id is not None and str(task_id):
                by_id[source][str(task_id)].add(path)
            mappings.append(dict(source=source, record_index=number, task_id=task_id,
                                 original_video=reference, local_video=path, method=method))
            methods[f"{source}:{method}"] += 1
            converted = dict(record)
            if source == "csv":
                converted["video"] = path
                local_rows.append(converted)
            else:
                converted["data"] = dict(record["data"], video=path)
                local_tasks.append(converted)
    common_ids = set(by_id["csv"]) & set(by_id["json"])
    for task_id in common_ids:
        require(by_id["csv"][task_id] == by_id["json"][task_id]
                and len(by_id["csv"][task_id]) == 1,
                f"CSV/JSON video disagreement for task ID {task_id}")
    return local_rows, local_tasks, mappings, dict(methods), len(common_ids)


def compare_annotations(fields, rows, tasks, local_fields, local_rows, local_tasks,
                        expected_rows, expected_tasks):
    require(fields == local_fields and len(rows) == len(local_rows), "CSV shape/order changed")
    for number, (before, after, expected) in enumerate(zip(rows, local_rows, expected_rows), 1):
        require(all(before[key] == after[key] for key in fields if key != "video"),
                f"Non-address CSV content changed at row {number}")
        require(after["video"] == expected["video"], f"Incorrect CSV video address at row {number}")
    require(isinstance(local_tasks, list) and len(tasks) == len(local_tasks), "JSON task count changed")
    for number, (before, after, expected) in enumerate(zip(tasks, local_tasks, expected_tasks), 1):
        require(json_without_video(before) == json_without_video(after),
                f"Non-address JSON content changed at task {number}")
        require(task_video(after) == task_video(expected), f"Incorrect JSON video address at task {number}")


def check_sources(sources, index, referenced):
    for path, original in sources.items():
        require(digest(path.read_bytes()) == digest(original), f"Source annotation changed: {path}")
    for name in referenced:
        path = Path(name)
        stat = path.stat()
        require((stat.st_size, stat.st_mtime_ns, stat.st_ino) == index.stats[path],
                f"Referenced video size/mtime/inode changed: {path.name}")


def checked_destination(path, root):
    path = path.resolve()
    require(root in path.parents, "Output must stay inside the project directory")
    return path


def preflight(path, data):
    require(not path.is_symlink(), "Refusing a symlink destination")
    if os.path.lexists(path):
        require(path.is_file() and path.read_bytes() == data,
                f"Existing output differs; refusing to overwrite: {path}")


def publish(path, data):
    preflight(path, data)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Atomic create without overwriting a destination created concurrently.
            os.link(temporary, path)
            return True
        except FileExistsError:
            preflight(path, data)
            return False
    finally:
        temporary.unlink(missing_ok=True)


def self_test():
    root = Path("/fixture").resolve()
    names = {name: [root / name] for name in
             ("cat 甲%20.mp4", "1234abcd-original.mp4", "original.mp4")}
    index = VideoIndex(root, names, {})
    require(index.resolve("/data/local-files/?d=dir%2Fcat%20%E7%94%B2%2520.mp4")[0]
            == str(root / "cat 甲%20.mp4"), "Single-decode query contract failed")
    require(index.resolve("/data/upload/1/1234abcd-original.mp4")[0]
            == str(root / "1234abcd-original.mp4"), "Exact filename must precede prefix stripping")
    require(index.resolve("/data/upload/1/deadbeef-original.mp4")[0]
            == str(root / "original.mp4"), "Upload prefix mapping failed")
    require(index.resolve(str(root / "original.mp4"))[1] == "absolute", "Idempotent path failed")
    for bad in ("/data/local-files/?d=original.mp4&d=original.mp4", "/data/local-files/?d=missing.mp4",
                "/data/upload/1/._original.mp4", str(root / "../outside.mp4")):
        try:
            index.resolve(bad)
        except MappingError:
            pass
        else:
            raise MappingError("Invalid/ambiguous reference was accepted")
    ambiguous = VideoIndex(root, {"same.mp4": [root / "a/same.mp4", root / "b/same.mp4"]}, {})
    try:
        ambiguous.resolve("/data/local-files/?d=same.mp4")
    except MappingError:
        pass
    else:
        raise MappingError("Duplicate basename was accepted")
    behavior = ' [{"ranges":[{"start":1,"end":9}],"timelinelabels":["动作甲"]}] '
    rows = [{"id": "1", "video": "/data/local-files/?d=original.mp4", "behavior": behavior},
            {"id": "2", "video": "/data/upload/1/deadbeef-original.mp4", "behavior": ""}]
    tasks = [{"id": 1, "data": {"video": rows[0]["video"], "keep": "原值"},
              "annotations": [{"was_cancelled": True, "result": [{"value": behavior}]}]},
             {"id": 2, "data": {"video": rows[1]["video"]}, "annotations": []}]
    fields = list(rows[0])
    new_rows, new_tasks, _, _, common = normalize(rows, tasks, index)
    actual_fields, actual_rows = read_csv(csv_bytes(fields, new_rows))
    actual_tasks = json.loads(json_bytes(new_tasks))
    compare_annotations(fields, rows, tasks, actual_fields, actual_rows, actual_tasks, new_rows, new_tasks)
    require(actual_rows[0]["behavior"] == behavior and actual_rows[1]["behavior"] == "" and common == 2,
            "Non-address/empty-annotation preservation failed")
    print("SELF_TEST_PASS: URL decoding, exact-before-prefix, idempotence, rejection, annotation preservation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path, default=Path("/home/work/pet_analysis_wyy"))
    parser.add_argument("--output-dir", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-only", action="store_true", help="Map and validate in RAM; write nothing")
    modes.add_argument("--verify-only", action="store_true", help="Verify existing normalized copies; write nothing")
    modes.add_argument("--self-test", action="store_true", help="Run in-memory contract checks on the remote server")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    root, data_root = args.root.resolve(strict=True), args.data_root.resolve(strict=True)
    output = checked_destination(args.output_dir or root / "datasets/company_video_paths", root)
    require(not (data_root == output or data_root in output.parents), "Output cannot be in the source dataset")
    sources = {data_root / "annotation-wyy" / f"merged_annotations.{suffix}": None
               for suffix in ("csv", "json")}
    sources = {path: path.read_bytes() for path in sources}
    fields, rows = read_csv(sources[data_root / "annotation-wyy/merged_annotations.csv"])
    tasks = json.loads(sources[data_root / "annotation-wyy/merged_annotations.json"].decode("utf-8-sig"))
    index = VideoIndex.scan(data_root / "dataset-wyy")
    new_rows, new_tasks, mappings, methods, common = normalize(rows, tasks, index)
    referenced = sorted({item["local_video"] for item in mappings})
    for name in referenced:
        with Path(name).open("rb") as handle:
            handle.read(1)
    compare_annotations(fields, rows, tasks, fields, new_rows, new_tasks, new_rows, new_tasks)
    check_sources(sources, index, referenced)
    outputs = {output / "merged_annotations.local.csv": csv_bytes(fields, new_rows),
               output / "merged_annotations.local.json": json_bytes(new_tasks)}
    report = dict(csv_rows=len(rows), json_tasks=len(tasks), mapped_csv=len(new_rows), mapped_json=len(new_tasks),
                  unique_referenced_videos=len(referenced), indexed_video_files=sum(map(len, index.names.values())),
                  ignored_appledouble_files=index.appledouble, mapping_methods=methods,
                  cross_source_task_ids_checked=common, all_referenced_videos_readable=True,
                  non_address_csv_values_unchanged=True, non_address_json_values_unchanged=True,
                  source_sha256={str(path): digest(data) for path, data in sources.items()},
                  source_annotations_unchanged=True, referenced_video_size_mtime_inode_unchanged=True,
                  output_csv=str(output / "merged_annotations.local.csv"),
                  output_json=str(output / "merged_annotations.local.json"))
    if args.check_only:
        report["mode"] = "check-only"
    elif args.verify_only:
        local_fields, local_rows = read_csv((output / "merged_annotations.local.csv").read_bytes())
        local_tasks = json.loads((output / "merged_annotations.local.json").read_text(encoding="utf-8-sig"))
        compare_annotations(fields, rows, tasks, local_fields, local_rows, local_tasks, new_rows, new_tasks)
        check_sources(sources, index, referenced)
        report["mode"] = "verify-only"
    else:
        for path, data in outputs.items():
            preflight(path, data)
        created = []
        try:
            for path, data in outputs.items():
                if publish(path, data):
                    created.append(path)
            local_fields, local_rows = read_csv((output / "merged_annotations.local.csv").read_bytes())
            local_tasks = json.loads((output / "merged_annotations.local.json").read_text(encoding="utf-8-sig"))
            compare_annotations(fields, rows, tasks, local_fields, local_rows, local_tasks, new_rows, new_tasks)
            check_sources(sources, index, referenced)
            report["mode"] = "normalize"
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
            audit_dir = checked_destination(root / "results/datasets" / ("company_video_paths_" + stamp), root)
            report["audit_dir"] = str(audit_dir)
            report["output_sha256"] = {str(path): digest(path.read_bytes()) for path in outputs}
            map_fields = ["source", "record_index", "task_id", "original_video", "local_video", "method"]
            publish(audit_dir / "path_mapping.csv", csv_bytes(map_fields, mappings))
            publish(audit_dir / "report.json", json_bytes(report))
        except Exception:
            # These are only files created by this invocation inside the validated project output path.
            for path in created:
                path.unlink(missing_ok=True)
            raise
    print("COMPANY_VIDEO_PATHS_DONE " + json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    try:
        raise SystemExit(main())
    except (MappingError, OSError, ValueError, KeyError) as exc:
        print(f"COMPANY_VIDEO_PATHS_FAILED {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
