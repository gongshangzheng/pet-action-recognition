"""Select detection frames on the source video's global five-frame phase."""


def select_frame_indices(frame_count: int, start: int | None = None, end: int | None = None) -> range:
    """Select zero-based frames within an inclusive interval, or the full video."""
    if frame_count < 0:
        raise ValueError('frame count must be nonnegative')
    if start is None and end is None:
        return range(0, frame_count, 5)
    if start is None or end is None or start < 0 or end < start or end >= frame_count:
        raise ValueError('invalid inclusive frame interval')
    return range(((start + 4) // 5) * 5, end + 1, 5)
