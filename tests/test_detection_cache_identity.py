import json
import tempfile
from pathlib import Path

import pytest
from lib.detection.cache import validate_reuse
from lib.detection.fingerprint import build_fingerprint


@pytest.fixture
def files():
    root = Path(__file__).resolve().parents[1] / 'results/tests/detection-cache-identity'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as name:
        path = Path(name)
        for filename in ('video', 'weights', 'config'):
            (path / filename).write_bytes(filename.encode())
        yield path


def test_fingerprint_rejects_changed_sources_and_parameters(files):
    params = {'classes': ['cat', 'dog'], 'sample_stride': 5, 'box_threshold': 0.3}
    def fingerprint():
        return build_fingerprint(files / 'video', 'grounding_dino', files / 'weights', files / 'config', params)
    original = fingerprint()
    cache = {'fingerprint': original, 'frames': {'0': [], '5': []}}
    validate_reuse(cache, fingerprint(), [0, 5])
    for name in ('video', 'weights', 'config'):
        path = files / name
        before = path.read_bytes()
        path.write_bytes(before + b'changed')
        with pytest.raises(ValueError, match='fingerprint'):
            validate_reuse(cache, fingerprint(), [0])
        path.write_bytes(before)
    params['box_threshold'] = 0.4
    with pytest.raises(ValueError, match='fingerprint'):
        validate_reuse(cache, fingerprint(), [0])


def test_missing_frame_cannot_be_treated_as_empty(files):
    fingerprint = build_fingerprint(files / 'video', 'grounding_dino', files / 'weights', files / 'config', {'sample_stride': 5})
    cache_file = files / 'cache.json'
    cache_file.write_text(json.dumps({'fingerprint': fingerprint, 'frames': {'0': []}}))
    cache = json.loads(cache_file.read_text())
    validate_reuse(cache, fingerprint, [0])
    with pytest.raises(ValueError, match='missing'):
        validate_reuse(cache, fingerprint, [5])
    with pytest.raises(ValueError, match='fingerprint'):
        validate_reuse({'schema': 'legacy', 'anchors': {}}, fingerprint, [0])
