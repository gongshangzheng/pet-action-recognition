import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.annotation_coverage import build_annotation_coverage
from lib.datasets.interval_manifest import build_interval_manifest
from lib.datasets.interval_statistics import build_interval_statistics
from lib.datasets.video_manifest import build_video_manifest


@pytest.fixture
def inputs():
    root = Path(__file__).resolve().parents[1] / 'results/tests/annotation-coverage'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        base = Path(directory)
        source = base / 'videos'
        source.mkdir()
        names = ['a.mp4', 'empty.mp4', 'full.mp4', 'invalid.mp4', 'no_fps.mp4', 'no_n.mp4']
        for name in names:
            (source / name).write_bytes(b'path only')
        inv = base / 'inventory'
        inv_meta = build_video_manifest(source, inv)
        csv = base / 'intervals.csv'
        csv.write_text('video,start_frame,end_frame,label\n'
                       'videos/a.mp4,0,0,a\n'
                       'videos/a.mp4,2,4,a\n'
                       'videos/a.mp4,3,3,b\n'
                       'videos/a.mp4,2,4,a\n'
                       'videos/a.mp4,5,6,b\n'
                       'videos/full.mp4,0,9,a\n'
                       'videos/invalid.mp4,0,10,a\n'
                       'videos/no_fps.mp4,1,2,a\n'
                       'videos/no_n.mp4,0,0,a\n'
                       'videos/missing.mp4,0,1,a\n', encoding='utf-8')
        association = base / 'association'
        build_interval_manifest(inv, csv, 'videos', association)
        meta_hash = hashlib.sha256((inv / 'manifest.json').read_bytes()).hexdigest()
        video_stats = base / 'video_statistics.json'
        rows = [{'video_id': name, 'fps': None if name == 'no_fps.mp4' else 5.0,
                 'reported_frames': None if name == 'no_n.mp4' else 10.0} for name in names]
        video_stats.write_text(json.dumps({'metadata': {'format_version': 1, 'video_root': str(source),
                              'inventory_sha256': inv_meta['videos_sha256'],
                              'inventory_metadata_sha256': meta_hash}, 'videos': rows}))
        stats_dir = base / 'interval-stats'
        build_interval_statistics(association / 'interval_manifest.json', video_stats, stats_dir)
        yield base, stats_dir / 'interval_statistics.json', video_stats


def test_union_complement_and_unknown(inputs):
    base, stats, video = inputs
    output = base / 'out'
    build_annotation_coverage(stats, video, output)
    result = json.loads((output / 'annotation_coverage.json').read_text())
    rows = {x['video_id']: x for x in result['videos']}
    assert rows['a.mp4']['union_ranges'] == [[0, 1], [2, 7]]
    assert rows['a.mp4']['unannotated_ranges'] == [[1, 2], [7, 10]]
    assert rows['a.mp4']['union_frames'] == 6
    assert rows['a.mp4']['unannotated_sec'] == pytest.approx(0.8)
    assert rows['empty.mp4']['union_frames'] == 0
    assert rows['empty.mp4']['unannotated_ranges'] == [[0, 10]]
    assert rows['full.mp4']['unannotated_frames'] == 0
    assert rows['invalid.mp4']['union_ranges'] is None
    assert rows['no_n.mp4']['union_frames'] is None
    assert rows['no_fps.mp4']['union_ranges'] == [[1, 3]]
    assert rows['no_fps.mp4']['union_sec'] is None
    assert result['summary']['known_videos'] == 3
    assert result['summary']['unknown_videos'] == 3
    assert result['summary']['videos_without_annotations'] == 1
    assert result['summary']['reported_frames'] == 30
    assert result['summary']['union_frames'] == 16
    assert result['unmatched'][0]['reason'] == 'video_not_in_inventory'
    with pytest.raises(FileExistsError):
        build_annotation_coverage(stats, video, output)
    assert json.loads((output / 'annotation_coverage.json').read_text()) == result


def test_cli_errors_and_input_identity(inputs):
    base, stats, video = inputs
    output = base / 'out'
    run = subprocess.run([sys.executable, '-m', 'lib.datasets.annotation_coverage', '--interval-statistics', str(stats),
                          '--video-statistics', str(video), '--output-dir', str(output)], capture_output=True, text=True)
    assert run.returncode != 0
    assert 'invalid.mp4' in run.stderr and 'line 8' in run.stderr and 'end_out_of_bounds' in run.stderr
    assert 'no_fps.mp4' in run.stderr and 'missing_fps' in run.stderr
    assert 'video_not_in_inventory' in run.stderr
    video.write_text(video.read_text() + ' ')
    with pytest.raises(ValueError, match='video statistics'):
        build_annotation_coverage(stats, video, base / 'bad')
