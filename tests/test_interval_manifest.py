import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.interval_manifest import build_interval_manifest
from lib.datasets.video_manifest import build_video_manifest


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/interval-manifest'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def test_association_preserves_rows_and_inventory(workspace):
    source = workspace / 'videos'
    for name in ('a/same.mp4', 'b/same.mp4', 'unannotated.mp4'):
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'path only')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    annotations = workspace / 'intervals.csv'
    fields = ['video', 'task_id', 'start_frame', 'end_frame', 'label']
    rows = [
        ['videos/a/same.mp4', '7', '001', '29', 'common/activity'],
        ['videos/a/same.mp4', '8', '30', '88', 'common/grooming'],
        ['videos/b/same.mp4', '9', '4', '5', 'common/eating'],
        ['videos/missing.mp4', '10', '8', '9', 'other'],
        ['wrong/a/same.mp4', '11', '1', '2', 'x'],
        ['videos/../a/same.mp4', '12', '1', '2', 'y'],
    ]
    with annotations.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    output = workspace / 'output'
    build_interval_manifest(inventory, annotations, 'videos', output)
    result = json.loads((output / 'interval_manifest.json').read_text())
    videos = {item['video_id']: item['intervals'] for item in result['videos']}
    assert list(videos) == ['a/same.mp4', 'b/same.mp4', 'unannotated.mp4']
    assert videos['a/same.mp4'] == [
        {'source_line': i + 2, 'fields': dict(zip(fields, rows[i]))} for i in (0, 1)]
    assert videos['b/same.mp4'][0]['fields'] == dict(zip(fields, rows[2]))
    assert videos['unannotated.mp4'] == []
    assert [item['reason'] for item in result['unmatched']] == [
        'video_not_in_inventory', 'outside_video_prefix', 'invalid_video_path']
    assert [item['fields'] for item in result['unmatched']] == [dict(zip(fields, row)) for row in rows[3:]]
    assert result['metadata']['annotations_sha256'] == hashlib.sha256(annotations.read_bytes()).hexdigest()
    assert result['metadata']['inventory_sha256'] == hashlib.sha256((inventory / 'videos.jsonl').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        build_interval_manifest(inventory, annotations, 'videos', output)
    assert json.loads((output / 'interval_manifest.json').read_text()) == result


def test_cli_checks_inventory_hash(workspace):
    source = workspace / 'videos'
    source.mkdir()
    (source / 'one.mp4').write_bytes(b'')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    annotations = workspace / 'intervals.csv'
    annotations.write_text('video,label\none.mp4,label\n', encoding='utf-8')
    output = workspace / 'output'
    subprocess.run([sys.executable, '-m', 'lib.datasets.interval_manifest', '--inventory-dir', str(inventory),
                    '--annotations', str(annotations), '--video-prefix', '.', '--output-dir', str(output)], check=True)
    assert json.loads((output / 'interval_manifest.json').read_text())['videos'][0]['intervals'][0]['fields']['label'] == 'label'
    (inventory / 'videos.jsonl').write_text('', encoding='utf-8')
    with pytest.raises(ValueError, match='inventory'):
        build_interval_manifest(inventory, annotations, '.', workspace / 'another')
