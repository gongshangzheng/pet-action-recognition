import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from lib.datasets.video_manifest import build_video_manifest
from lib.datasets.video_statistics import build_video_statistics


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/video-statistics'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def test_statistics_and_historical_diagnostics(workspace):
    source = workspace / 'videos'
    source.mkdir()
    video = source / 'good.avi'
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 5, (32, 32))
    assert writer.isOpened()
    for _ in range(6):
        writer.write(np.zeros((32, 32, 3), dtype=np.uint8))
    writer.release()
    (source / 'broken.mp4').write_bytes(b'not a video')
    missing = source / 'missing.mp4'
    missing.write_bytes(b'will be removed')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    missing.unlink()
    audit = workspace / 'audit.json'
    audit.write_text(json.dumps({'failed': [{'video': 'videos/absent.mp4', 'status': 'source_unreadable'},
                                             {'video': 'videos/good.avi', 'status': 'source_unreadable',
                                              'error': 'historical failure'}],
                                 'truncated': [{'video': 'videos/good.avi', 'reported': 457, 'decoded': 16,
                                                'status': 'source_decode_truncated'}]}))
    output = workspace / 'output'
    build_video_statistics(inventory, output, audit, 'videos')
    result = json.loads((output / 'video_statistics.json').read_text())
    rows = {row['video_id']: row for row in result['videos']}
    assert rows['good.avi']['status'] == 'known'
    assert rows['good.avi']['reported_frames'] == 6
    assert rows['good.avi']['fps'] == pytest.approx(5)
    assert rows['good.avi']['duration_sec'] == pytest.approx(1.2)
    assert rows['good.avi']['known_source_diagnostics'][1]['decoded'] == 16
    assert rows['broken.mp4']['reason'] == 'open_failed'
    assert rows['missing.mp4']['reason'] == 'open_failed'
    assert rows['broken.mp4']['duration_sec'] is None
    assert result['summary']['videos_total'] == 3
    assert result['summary']['known'] == 1
    assert result['summary']['unknown'] == 2
    assert result['summary']['duration_sec']['median'] == pytest.approx(1.2)
    assert result['unmatched_quality_diagnostics'][0]['video'] == 'videos/absent.mp4'
    completed = subprocess.run(
        [sys.executable, '-m', 'lib.datasets.video_statistics', '--inventory-dir', str(inventory),
         '--output-dir', str(workspace / 'cli-out'), '--quality-audit', str(audit),
         '--audit-video-prefix', 'videos'], capture_output=True, text=True)
    assert completed.returncode != 0
    assert f'ERROR {source / "broken.mp4"}: open_failed' in completed.stderr
    assert f'ERROR {source / "missing.mp4"}: open_failed' in completed.stderr
    assert f'WARNING {video}: historical decode truncation reported=457 decoded=16' in completed.stderr
    assert f'WARNING {video}: historical source unreadable (not rechecked): historical failure' in completed.stderr
    with pytest.raises(FileExistsError):
        build_video_statistics(inventory, output, audit, 'videos')
    assert json.loads((output / 'video_statistics.json').read_text()) == result


def test_cli_and_inventory_hash(workspace):
    source = workspace / 'videos'
    source.mkdir()
    (source / 'bad.mp4').write_bytes(b'broken')
    inventory = workspace / 'inventory'
    build_video_manifest(source, inventory)
    output = workspace / 'out'
    completed = subprocess.run([sys.executable, '-m', 'lib.datasets.video_statistics', '--inventory-dir', str(inventory),
                                '--output-dir', str(output)], capture_output=True, text=True)
    assert completed.returncode != 0
    assert 'ERROR' in completed.stderr and str(source / 'bad.mp4') in completed.stderr
    assert 'open_failed' in completed.stderr
    result = json.loads((output / 'video_statistics.json').read_text())
    assert result['summary']['known'] == 0
    assert result['summary']['duration_sec']['mean'] is None
    (inventory / 'videos.jsonl').write_bytes(b'')
    with pytest.raises(ValueError, match='inventory'):
        build_video_statistics(inventory, workspace / 'bad-out')
