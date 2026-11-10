"""Content identity for a source video and detector configuration."""

import hashlib
import json
from pathlib import Path


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build_fingerprint(video, detector_family, weights, model_config, parameters):
    """Bind source and detector identity to content and explicit parameters."""
    if not detector_family or not isinstance(parameters, dict):
        raise ValueError('detector family and parameter dictionary are required')
    # Round-trip freezes caller-owned mutable parameters and rejects non-JSON values.
    params = json.loads(json.dumps(parameters, allow_nan=False, sort_keys=True))
    return {'version': 1, 'source_sha256': _sha256(video),
            'detector_family': detector_family, 'weights_sha256': _sha256(weights),
            'model_config_sha256': _sha256(model_config), 'parameters': params}
