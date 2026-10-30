#!/usr/bin/env python3
"""Read-only check that every lab annotation path resolves on the lab server.

迁移验收缺口：Linux 路径版 CSV 存在、行数正确，不等于每行路径都可读。
本脚本在科研服务器上逐个检查标注引用的视频文件是否真实存在且非空，
结果写入本机 results/migration/lab_path_check.json，不改动远端任何文件。

用法：
    python3 scripts/checks/check_lab_annotation_paths.py            # 用 ~/.ssh/config 的 lab
    python3 scripts/checks/check_lab_annotation_paths.py --host lab
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "results" / "migration" / "lab_path_check.json"
REMOTE_ROOT = "/home/wyy/pet-final/datasets/cat_raw"

REMOTE_SCRIPT = r'''
import json
import os
from pathlib import Path

root = Path(''' + repr(REMOTE_ROOT) + r''')
annotations = root / 'annotations'
videos = root / 'videos'
report = {'root': str(root), 'checks': []}

def record(name, paths, *, base=None):
    base_path = Path(base) if base else None
    missing, empty, checked = [], [], 0
    for raw in paths:
        if not raw:
            continue
        target = Path(raw) if base_path is None else base_path / raw
        checked += 1
        if not target.is_file():
            if len(missing) < 30:
                missing.append(str(target))
            continue
        if target.stat().st_size == 0 and len(empty) < 30:
            empty.append(str(target))
    report['checks'].append({
        'name': name,
        'checked': checked,
        'missing': len(missing),
        'missing_samples': missing,
        'empty': len(empty),
        'empty_samples': empty,
    })

def column(csv_path, field):
    import csv
    if not csv_path.is_file():
        return None
    with csv_path.open(encoding='utf-8', newline='') as handle:
        return [row.get(field) for row in csv.DictReader(handle)]

lab_csv = annotations / 'merged_annotations.lab.csv'
lab_paths = column(lab_csv, 'video')
record('merged_annotations.lab.csv', lab_paths or [])

relative_csv = annotations / 'merged_annotations.relative.csv'
relative_paths = column(relative_csv, 'video')
record('merged_annotations.relative.csv', relative_paths or [], base=root)

intervals = annotations / 'intervals.csv'
interval_paths = column(intervals, 'video')
record('intervals.csv', interval_paths or [], base=root)

lab_json = annotations / 'merged_annotations.lab.json'
json_checked = 0
if lab_json.is_file():
    tasks = json.loads(lab_json.read_text(encoding='utf-8'))
    json_paths = [task.get('data', {}).get('video', '') for task in tasks]
    record('merged_annotations.lab.json', json_paths)
    json_checked = len(json_paths)

files = [p for p in videos.rglob('*') if p.is_file()]
report['videos_on_disk'] = len(files)
report['video_bytes_on_disk'] = sum(p.stat().st_size for p in files)
report['vid_ext'] = sorted({p.suffix.lower() for p in files})
report['json_tasks'] = json_checked
report['target_exists'] = root.is_dir()
print(json.dumps(report, ensure_ascii=False))
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="lab", help="~/.ssh/config 中的主机别名")
    args = parser.parse_args()

    command = ["ssh", args.host, "python3 -c " + shlex.quote(REMOTE_SCRIPT)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if completed.returncode != 0:
        print(completed.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"检查脚本在远端失败（exit={completed.returncode}）")

    report = json.loads(completed.stdout.strip().splitlines()[-1])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total_missing = 0
    for check in report["checks"]:
        total_missing += check["missing"]
        print(f"{check['name']:<34} checked={check['checked']:<6} "
              f"missing={check['missing']:<4} empty={check['empty']}")
        for sample in check["missing_samples"][:5]:
            print(f"    MISSING {sample}")
    print(f"videos_on_disk={report['videos_on_disk']} "
          f"bytes={report['video_bytes_on_disk']} ext={report['vid_ext']}")
    print(f"report -> {REPORT.relative_to(ROOT)}")
    if total_missing:
        raise SystemExit(f"有 {total_missing} 处标注路径读不到")


if __name__ == "__main__":
    main()
