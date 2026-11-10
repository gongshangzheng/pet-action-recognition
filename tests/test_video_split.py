import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.video_manifest import build_video_manifest


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/video-split'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def run_split(inventory, output):
    return subprocess.run([sys.executable, '-m', 'lib.datasets.video_split',
                           '--inventory-dir', str(inventory), '--output-dir', str(output),
                           '--seed', '0'], capture_output=True, text=True)


def test_split_covers_inventory_reproducibly_and_refuses_overwrite(workspace):
    source = workspace / 'source'
    source.mkdir()
    for i in range(20):
        (source / f'{i:02}.mp4').write_bytes(b'')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    first, second = workspace / 'first', workspace / 'second'
    assert run_split(inventory, first).returncode == 0
    assert run_split(inventory, second).returncode == 0
    result = json.loads((first / 'split.json').read_text())
    other = json.loads((second / 'split.json').read_text())
    assert result == other
    assert result['metadata']['inventory_sha256'] == hashlib.sha256((inventory / 'videos.jsonl').read_bytes()).hexdigest()
    assert result['metadata']['seed'] == 0
    assert result['metadata']['counts'] == {'train': 16, 'val': 2, 'test': 2}
    assert result['unassigned'] == []
    assert len(result['videos']) == 20
    assert {row['video_id'] for row in result['videos']} == {f'{i:02}.mp4' for i in range(20)}
    assert all(row['split'] in ('train', 'val', 'test') for row in result['videos'])
    before = (first / 'split.json').read_bytes()
    assert run_split(inventory, first).returncode != 0
    assert (first / 'split.json').read_bytes() == before


def test_tampered_inventory_is_rejected(workspace):
    source = workspace / 'source'
    source.mkdir()
    (source / 'one.mp4').write_bytes(b'')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    (inventory / 'videos.jsonl').write_text('{}\n')
    output = workspace / 'output'
    result = run_split(inventory, output)
    assert result.returncode != 0
    assert 'inventory metadata mismatch' in result.stderr
    assert not output.exists()
