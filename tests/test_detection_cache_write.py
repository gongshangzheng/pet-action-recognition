import json
import tempfile
from pathlib import Path

import pytest

from lib.detection.cache import validate_reuse, write_video_cache


def test_write_one_file_per_video_with_real_empty_and_missing_frames():
    root = Path(__file__).resolve().parents[1] / 'results/tests/detection-cache-write'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        version = Path(directory)
        fingerprint = {'version': 1, 'source_sha256': 'source', 'parameters': {'sample_stride': 5}}
        records = [{'frame': 0, 'candidates': [{'class': 'cat', 'box': [1, 2, 3, 4], 'confidence': 0.9}]},
                   {'frame': 5, 'candidates': []}]
        output = write_video_cache(version, 'a/same.mp4', fingerprint, records)
        saved = json.loads(output.read_text())
        assert saved['video_id'] == 'a/same.mp4'
        assert saved['fingerprint'] == fingerprint
        assert saved['frames'] == {'0': records[0]['candidates'], '5': []}
        validate_reuse(saved, fingerprint, [0, 5])
        with pytest.raises(ValueError, match='missing'):
            validate_reuse(saved, fingerprint, [10])
        other = write_video_cache(version, 'b/same.mp4', fingerprint, records)
        assert other != output
        before = output.read_bytes()
        with pytest.raises(FileExistsError):
            write_video_cache(version, 'a/same.mp4', fingerprint, records)
        assert output.read_bytes() == before
