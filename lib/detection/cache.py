"""Save detector results and reject mismatched or incomplete reuse."""

import hashlib
import json
from pathlib import Path


def validate_reuse(cache, expected_fingerprint, requested_frames):
    """Check identity and real frame coverage; an empty candidate list is a detection."""
    if cache.get('fingerprint') != expected_fingerprint:
        raise ValueError('detection cache fingerprint mismatch')
    frames = cache.get('frames')
    if not isinstance(frames, dict):
        raise ValueError('detection cache frames missing')
    missing = [frame for frame in requested_frames if str(frame) not in frames]
    if missing:
        raise ValueError(f'detection cache missing frames: {missing}')


def write_video_cache(version_dir, video_id, fingerprint, records):
    """Create one new video result without overwriting an existing version."""
    if not isinstance(video_id, str) or not video_id:
        raise ValueError('video_id is required')
    frames = {}
    for record in records:
        frame = record['frame']
        if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
            raise ValueError('invalid frame index')
        key = str(frame)
        if key in frames or not isinstance(record['candidates'], list):
            raise ValueError('duplicate frame or invalid candidates')
        frames[key] = record['candidates']
    payload = {'format_version': 1, 'video_id': video_id,
               'fingerprint': fingerprint, 'frames': frames}
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
    target = Path(version_dir) / (hashlib.sha256(video_id.encode('utf-8')).hexdigest() + '.json')
    with target.open('x', encoding='utf-8') as stream:
        try:
            stream.write(encoded)
        except BaseException:
            target.unlink()
            raise
    return target
