import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.annotation_overlaps import build_annotation_overlaps


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/annotation-overlaps'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def make_input(base, extra=()):
    # These are file-contract inputs, not measured media attributes.
    rows = []
    for line, video, start, end, label, status, reason in [
        (2, 'a.mp4', 0, 10, 'rest', 'known', None),
        (3, 'a.mp4', 10, 20, 'drink', 'known', None),
        (4, 'a.mp4', 0, 10, 'rest', 'known', None),
        (5, 'a.mp4', 2, 4, 'scratch', 'known', None),
        (6, 'a.mp4', 21, 25, 'drink', 'known', None),
        (7, 'b.mp4', 0, 10, 'rest', 'known', None),
        *extra,
    ]:
        rows.append({'video_id': video, 'source_line': line,
                     'fields': {'video': f'videos/{video}', 'start_frame': str(start),
                                'end_frame': str(end), 'label': label, 'result_id': f'r{line}'},
                     'status': status, 'reason': reason})
    result = {'metadata': {'format_version': 1, 'frame_convention': 'zero-based inclusive',
                           'video_root': str(base / 'videos')},
              'intervals': rows, 'unmatched': []}
    path = base / 'interval_statistics.json'
    path.write_text(json.dumps(result), encoding='utf-8')
    return path


def test_overlap_pairs_and_provenance(workspace):
    source = make_input(workspace)
    before = source.read_bytes()
    output = workspace / 'out'
    build_annotation_overlaps(source, output)
    result = json.loads((output / 'annotation_overlaps.json').read_text())
    pairs = {(p['left']['source_line'], p['right']['source_line']): p for p in result['pairs']}
    assert set(pairs) == {(2, 3), (2, 4), (2, 5), (3, 4), (4, 5)}
    assert pairs[2, 3]['intersection'] == {'start_frame': 10, 'end_frame': 10, 'frame_count': 1}
    assert pairs[2, 4]['kind'] == 'same_label'
    assert pairs[2, 5]['intersection'] == {'start_frame': 2, 'end_frame': 4, 'frame_count': 3}
    assert pairs[2, 5]['right']['fields']['result_id'] == 'r5'
    assert result['summary'] == {'same_label': {'pair_count': 1, 'video_count': 1},
                                 'different_label': {'pair_count': 4, 'video_count': 1},
                                 'affected_interval_count': 4, 'affected_video_count': 1,
                                 'error_count': 0, 'unmatched_count': 0, 'complete': True}
    assert [r['source_line'] for r in result['affected_intervals']] == [2, 3, 4, 5]
    assert all(r['review_status'] == 'pending' for r in result['affected_intervals'])
    assert result['metadata']['interval_statistics_sha256'] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before
    with pytest.raises(FileExistsError):
        build_annotation_overlaps(source, output)
    assert json.loads((output / 'annotation_overlaps.json').read_text()) == result


def test_cli_reports_invalid_unknown_and_unmatched(workspace):
    source = make_input(workspace, extra=[
        (8, 'a.mp4', -1, 2, 'rest', 'invalid', 'invalid_frame_range'),
        (9, 'b.mp4', 10, 12, 'drink', 'unknown', 'missing_fps'),
    ])
    data = json.loads(source.read_text())
    data['unmatched'] = [{'source_line': 10, 'fields': {'video': 'videos/missing.mp4'},
                          'reason': 'video_not_in_inventory'}]
    source.write_text(json.dumps(data))
    output = workspace / 'out'
    run = subprocess.run([sys.executable, '-m', 'lib.datasets.annotation_overlaps',
                          '--interval-statistics', str(source), '--output-dir', str(output)],
                         capture_output=True, text=True)
    assert run.returncode == 1
    for text in ('a.mp4 line 8: invalid_frame_range', 'b.mp4 line 9: missing_fps',
                 'videos/missing.mp4 line 10: video_not_in_inventory'):
        assert text in run.stderr
    result = json.loads((output / 'annotation_overlaps.json').read_text())
    assert result['summary']['complete'] is False
    assert result['summary']['error_count'] == 2
    assert result['unmatched'] == data['unmatched']
    assert [row['source_line'] for row in result['errors']] == [8, 9]
    assert all(8 not in (p['left']['source_line'], p['right']['source_line']) for p in result['pairs'])
    pair = next(p for p in result['pairs'] if p['video_id'] == 'b.mp4')
    assert pair['intersection'] == {'start_frame': 10, 'end_frame': 10, 'frame_count': 1}
    assert pair['right']['reason'] == 'missing_fps'
    data['metadata']['frame_convention'] = 'one-based inclusive'
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='frame convention'):
        build_annotation_overlaps(source, workspace / 'bad')
    assert not (workspace / 'bad').exists()
