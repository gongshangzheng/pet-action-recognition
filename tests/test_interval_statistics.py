import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.interval_manifest import build_interval_manifest
from lib.datasets.interval_statistics import build_interval_statistics
from lib.datasets.video_manifest import build_video_manifest


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/interval-statistics'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def make_inputs(workspace):
    source = workspace / 'videos'
    source.mkdir()
    for name in ('a.mp4', 'b.mp4', 'empty.mp4'):
        (source / name).write_bytes(b'path fixture')
    inventory = workspace / 'inventory'
    meta = build_video_manifest(source, inventory)
    annotations = workspace / 'intervals.csv'
    annotations.write_text('video,start_frame,end_frame,label\n'
                           'videos/a.mp4,0,0,cat\n'
                           'videos/a.mp4,1,5,cat\n'
                           'videos/a.mp4,1,5,cat\n'
                           'videos/a.mp4,3,7,dog\n'
                           'videos/b.mp4,0,4,cat\n'
                           'videos/a.mp4,9,10,dog\n'
                           'videos/a.mp4,-1,2,dog\n'
                           'videos/missing.mp4,0,1,cat\n', encoding='utf-8')
    association = workspace / 'association'
    build_interval_manifest(inventory, annotations, 'videos', association)
    interval_file = association / 'interval_manifest.json'
    association_metadata = json.loads(interval_file.read_text())['metadata']
    stats_file = workspace / 'video_statistics.json'
    stats_file.write_text(json.dumps({'metadata': {'format_version': 1, 'video_root': str(source),
                           'inventory_sha256': meta['videos_sha256'],
                           'inventory_metadata_sha256': association_metadata['inventory_metadata_sha256']},
                           'videos': [{'video_id': 'a.mp4', 'fps': 5.0, 'reported_frames': 10.0},
                                      {'video_id': 'b.mp4', 'fps': None, 'reported_frames': 10.0},
                                      {'video_id': 'empty.mp4', 'fps': 5.0, 'reported_frames': 10.0}]}))
    return interval_file, stats_file


def test_interval_statistics_accounting(workspace):
    association, video_stats = make_inputs(workspace)
    out = workspace / 'output'
    build_interval_statistics(association, video_stats, out)
    result = json.loads((out / 'interval_statistics.json').read_text())
    assert result['summary']['videos_without_intervals'] == 1
    assert result['summary']['unmatched_count'] == 1
    assert result['unmatched'][0]['reason'] == 'video_not_in_inventory'
    cat = result['labels']['cat']
    assert cat['interval_count'] == 4 and cat['video_count'] == 2
    assert cat['total_frames'] == 16
    assert cat['duration_known'] == 3 and cat['duration_unknown'] == 1
    assert cat['duration_sec']['total'] == pytest.approx(2.2)
    assert cat['duration_sec']['median'] == pytest.approx(1.0)
    assert result['labels']['dog']['interval_count'] == 3
    assert [row['reason'] for row in result['intervals'] if row['reason']] == [
        'end_out_of_bounds', 'invalid_frame_range', 'missing_fps']
    assert result['intervals'][0]['frame_count'] == 1
    assert result['intervals'][0]['fields']['start_frame'] == '0'
    with pytest.raises(FileExistsError):
        build_interval_statistics(association, video_stats, out)
    assert json.loads((out / 'interval_statistics.json').read_text()) == result


def test_cli_failure_and_mismatched_inventory(workspace):
    association, video_stats = make_inputs(workspace)
    out = workspace / 'output'
    run = subprocess.run([sys.executable, '-m', 'lib.datasets.interval_statistics', '--interval-manifest', str(association),
                          '--video-statistics', str(video_stats), '--output-dir', str(out)], capture_output=True, text=True)
    assert run.returncode != 0
    assert 'ERROR' in run.stderr and 'a.mp4' in run.stderr and 'line 7' in run.stderr
    assert 'video_not_in_inventory' in run.stderr and 'missing_fps' in run.stderr
    data = json.loads(video_stats.read_text())
    data['metadata']['inventory_sha256'] = 'wrong'
    video_stats.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='inventory'):
        build_interval_statistics(association, video_stats, workspace / 'bad')
