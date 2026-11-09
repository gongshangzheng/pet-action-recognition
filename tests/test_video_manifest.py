import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lib.datasets.video_manifest import build_video_manifest, validate_records


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / 'results/tests/video-manifest'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        yield Path(directory)


def test_directory_inventory_and_version(workspace):
    source = workspace / 'source'
    for name in ('z/same.mp4', 'a/same.mp4', 'unannotated.MP4', 'notes.txt'):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'not decoded')
    output = workspace / 'versions' / 'v1'
    build_video_manifest(source, output)
    data = (output / 'videos.jsonl').read_bytes()
    records = [json.loads(line) for line in data.splitlines()]
    assert records == [{'video_id': p, 'path': p} for p in
                       ['a/same.mp4', 'unannotated.MP4', 'z/same.mp4']]
    metadata = json.loads((output / 'manifest.json').read_text())
    assert metadata == {'format_version': 1, 'video_root': str(source.resolve()),
                        'count': 3, 'videos_sha256': hashlib.sha256(data).hexdigest()}
    with pytest.raises(FileExistsError):
        build_video_manifest(source, output)
    assert (output / 'videos.jsonl').read_bytes() == data


def test_duplicate_records_are_rejected():
    with pytest.raises(ValueError, match='duplicate video_id'):
        validate_records([{'video_id': 'a.mp4', 'path': 'a.mp4'},
                          {'video_id': 'a.mp4', 'path': 'other.mp4'}])


def test_empty_and_missing_source(workspace):
    empty = workspace / 'empty'
    empty.mkdir()
    with pytest.raises(ValueError, match='no video'):
        build_video_manifest(empty, workspace / 'v1')
    with pytest.raises(NotADirectoryError):
        build_video_manifest(workspace / 'missing', workspace / 'v2')


def test_cli_and_symlinks(workspace):
    source = workspace / 'source'
    source.mkdir()
    (source / 'one.mp4').write_bytes(b'')
    (source / 'link.mp4').symlink_to(source / 'one.mp4')
    (source / 'dir-link').symlink_to(workspace, target_is_directory=True)
    output = workspace / 'v1'
    subprocess.run([sys.executable, '-m', 'lib.datasets.video_manifest', '--video-root',
                    str(source), '--output-dir', str(output)], check=True)
    assert [json.loads(line)['path'] for line in (output / 'videos.jsonl').read_text().splitlines()] == ['one.mp4']
