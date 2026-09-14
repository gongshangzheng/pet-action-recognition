"""契约冒烟测试：petlib 所有注册实现必须通过统一接口 + schema 校验。

运行（repo 根）：
    PYTHONPATH=. ~/miniconda3/envs/plf/bin/python -m pytest petlib/contract_tests.py -v

GPU/重依赖缺失的实现自动 skip（不阻塞 CI）。
"""
from __future__ import annotations

import numpy as np
import pytest

from petlib.registry import available, create
from petlib.schemas import Detection, KeypointSequence, Track, TrackPoint


# ---------- fixtures ----------

@pytest.fixture
def synthetic_frame():
    """640×640 的带纹理灰度帧（检测冒烟用）。"""
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (360, 640, 3), dtype=np.uint8)


@pytest.fixture
def moving_cat_detections():
    """10 帧匀速右移的猫检测（x 从 100 → 280）。"""
    out = []
    for i in range(10):
        x1 = 100 + 20 * i
        out.append([Detection(frame=i, box=(x1, 200, x1 + 120, 320), conf=0.9)])
    return out


# ---------- schemas ----------

def test_schemas_detection():
    d = Detection(frame=0, box=(10.0, 20.0, 110.0, 220.0), conf=0.9)
    assert d.width == 100 and d.height == 200


def test_schemas_track_valid_and_invalid():
    good = Track(1, [TrackPoint(0, (0, 0, 10, 10), 0.9), TrackPoint(1, (2, 0, 12, 10), 0.8)])
    assert good.is_valid()
    bad = Track(1, [TrackPoint(1, (0, 0, 10, 10), 0.9), TrackPoint(0, (2, 0, 12, 10), 0.8)])
    assert not bad.is_valid()  # frame 倒序


def test_schemas_keypoint_npz_roundtrip(tmp_path):
    kp = np.zeros((12, 17, 3), dtype=np.float32)
    kp[..., :2] = 10.0
    kp[..., 2] = 0.9
    seq = KeypointSequence(kp=kp, frame_inds=list(range(12)), total_frames=48, source="unit-test")
    d = seq.to_npz_dict()
    assert d["keypoints"].shape == (12, 17, 3)
    assert d["keypoints"].dtype == np.float16


# ---------- registry ----------

def test_registry_lists_trackers():
    names = available("tracker")
    for n in ["byte_track", "oc_sort", "bot_sort", "deep_sort"]:
        assert n in names, n


def test_registry_create_tracker():
    t = create("tracker", "byte_track")
    assert hasattr(t, "update") and hasattr(t, "finalize")


def test_registry_unknown_name_raises():
    with pytest.raises(KeyError):
        create("tracker", "no_such_tracker")


# ---------- trackers（四实现同一契约）----------

TRACKER_NAMES = ["byte_track", "oc_sort", "bot_sort", "deep_sort"]


@pytest.mark.parametrize("name", TRACKER_NAMES)
def test_tracker_contract(name, moving_cat_detections):
    tracker = create("tracker", name)
    for fi, dets in enumerate(moving_cat_detections):
        tracks = tracker.update(dets, frame_idx=fi)
        for t in tracks:
            assert isinstance(t, Track) and t.is_valid()
    final = tracker.finalize()
    assert any(len(t.boxes) >= 8 for t in final), f"{name}: 轨迹碎片化（最长 {max(len(t.boxes) for t in final) if final else 0} 点）"


@pytest.mark.parametrize("name", TRACKER_NAMES)
def test_tracker_no_dets_no_crash(name):
    tracker = create("tracker", name)
    for fi in range(5):
        tracks = tracker.update([], frame_idx=fi)
        assert isinstance(tracks, list)
    assert tracker.finalize() is not None


# ---------- detector（需要权重 + CUDA，缺失则 skip）----------

def test_detector_grounding_dino_smoke(synthetic_frame):
    from pathlib import Path

    import torch

    weights = Path("~/models/grounding-dino-tiny").expanduser()
    if not (weights / "model.safetensors").exists() or not torch.cuda.is_available():
        pytest.skip("GroundingDINO 权重或 CUDA 不可用")
    det = create("detector", "grounding_dino")
    out = det.detect(synthetic_frame, classes=("cat",))
    assert isinstance(out, list)


# ---------- keypoints（重依赖缺失则 skip）----------

def test_keypoints_registry():
    from petlib.registry import available
    names = available("keypoints")
    assert "vitpose_ap10k" in names  # mmpose 缺失时会缺席
