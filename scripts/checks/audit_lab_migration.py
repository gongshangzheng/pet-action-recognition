#!/usr/bin/env python3
"""Read-only audit of the copied lab project and its existing Python environment."""
from __future__ import annotations

import json
import shlex

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.migration.migrate_pet_final_to_lab import LOCAL_REPORT, connect, remote_run


REMOTE_AUDIT = r'''
import csv
import importlib
from importlib import metadata
import json
from pathlib import Path
import subprocess

root = Path('/home/wyy/pet-final')
old = Path('/home/wyy/pet-action-recognition')
annotations = root / 'datasets/cat_raw/annotations'
videos = root / 'datasets/cat_raw/videos'
with (annotations / 'merged_annotations.lab.csv').open(encoding='utf-8', newline='') as stream:
    rows = list(csv.DictReader(stream))
with (annotations / 'intervals.csv').open(encoding='utf-8', newline='') as stream:
    intervals = list(csv.DictReader(stream))
with (annotations / 'merged_annotations.lab.json').open(encoding='utf-8') as stream:
    tasks = json.load(stream)
paths = [row['video'] for row in rows]
paths.extend(task['data']['video'] for task in tasks)
old_checkpoints = old / 'checkpoints'
checkpoint_files = sorted(str(p.relative_to(old_checkpoints)) for p in old_checkpoints.rglob('*') if p.is_file())
gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], capture_output=True, text=True)
result = {
    'target_exists': root.is_dir(),
    'original_project_exists': old.is_dir(),
    'video_files': sum(1 for p in videos.rglob('*') if p.is_file()),
    'csv_rows': len(rows),
    'json_tasks': len(tasks),
    'intervals': len(intervals),
    'lab_video_paths_checked': len(paths),
    'lab_video_paths_missing': [p for p in paths if not Path(p).is_file()][:20],
    'checkpoint_files': checkpoint_files[:200],
    'checkpoint_file_count': len(checkpoint_files),
    'gpus': gpu.stdout.strip().splitlines() if gpu.returncode == 0 else [gpu.stderr.strip()],
}
print(json.dumps(result, ensure_ascii=False))
'''

REMOTE_ENV = r'''
import importlib
from importlib import metadata
import json
import sys
import torch

names = ['torch', 'torchvision', 'mmcv', 'mmengine', 'mmaction2', 'mmdet',
         'decord', 'av', 'ultralytics', 'rembg', 'onnxruntime', 'rknn-toolkit2',
         'fastapi', 'uvicorn']
versions = {}
for name in names:
    try:
        versions[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        versions[name] = None
imports = {}
for name in ['mmaction', 'mmcv', 'mmengine', 'mmdet', 'decord', 'ultralytics', 'rembg']:
    try:
        importlib.import_module(name)
        imports[name] = 'ok'
    except Exception as exc:
        imports[name] = type(exc).__name__ + ': ' + str(exc)[:200]
print(json.dumps({'python': sys.version.split()[0], 'torch_cuda': torch.version.cuda,
                  'cuda_available': torch.cuda.is_available(),
                  'versions': versions, 'imports': imports}, ensure_ascii=False))
'''


def main() -> None:
    client = connect()
    try:
        commands = {
            'files_and_data': 'python3 -c ' + shlex.quote(REMOTE_AUDIT),
            'environment': '/home/wyy/miniconda3/envs/pet/bin/python -c ' + shlex.quote(REMOTE_ENV),
        }
        report = {}
        for name, command in commands.items():
            status, out, err = remote_run(client, command, checked=False)
            report[name] = json.loads(out) if status == 0 else {'exit_code': status, 'error': err[:2000]}
        LOCAL_REPORT.mkdir(parents=True, exist_ok=True)
        path = LOCAL_REPORT / 'lab_audit.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
