import pytest

from lib.detection.anchors import select_frame_indices


def test_full_video_and_interval_share_global_phase():
    assert list(select_frame_indices(12)) == [0, 5, 10]
    assert list(select_frame_indices(12, 1, 10)) == [5, 10]
    assert list(select_frame_indices(12, 5, 5)) == [5]
    assert list(select_frame_indices(12, 6, 9)) == []
    assert list(select_frame_indices(0)) == []


def test_invalid_intervals_are_rejected():
    for args in [(-1,), (10, -1, 5), (10, 5, 4), (10, 0, 10), (0, 0, 0)]:
        with pytest.raises(ValueError):
            list(select_frame_indices(*args))
