"""Reject reuse of mismatched or incomplete detector results."""


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
