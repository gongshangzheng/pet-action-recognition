#!/usr/bin/env python3
"""多宠物跟踪关联模式测试（multi-pet-sort-tracking 3.2 判据）。

判据（tasks 3.2）：合成用例中同一目标在物种标签抖动下保持同一 track id；
产物记录 species 与一致性比例。

夹具用项目 results/tests/ 下的临时目录（见 AGENTS.md 测试约定），不依赖系统 /tmp。
合成检测缓存：20 个锚点、stride=5、单只动物匀速右移；锚点 8–10 的物种标签
从 cat 翻成 dog（复现 2.4 在真实数据里观测到的物种抖动）。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.track_multi_pet import DEFAULT_PARAMS, track_video  # noqa: E402

STRIDE = 5
N_ANCHORS = 20
FLIP_FRAMES = {8, 9, 10}  # 物种标签抖动的锚点下标


def write_synthetic_cache(path: Path) -> None:
    """单只动物匀速右移；FLIP_FRAMES 上的锚点被标成 dog。"""
    anchors = {}
    for i in range(N_ANCHORS):
        x = 100 + 60 * i
        cls = "dog" if i in FLIP_FRAMES else "cat"
        box = [x, 100, x + 100, 240]
        state = {
            "cat_count": 0 if cls == "dog" else 1,
            "dog_count": 1 if cls == "dog" else 0,
            "pet_count": 1,
            "target_class": cls,
            "target_box": box,
            "target_confidence": 0.6,
            "cat_candidates": [] if cls == "dog" else [
                {"class": "cat", "box": box, "confidence": 0.6}],
            "dog_candidates": [{"class": "dog", "box": box, "confidence": 0.6}] if cls == "dog" else [],
            "reasons": [],
            "target_valid": True,
        }
        anchors[str(i * STRIDE)] = state
    payload = {
        "schema": "cat-crop-detection-v2",
        "status": "complete",
        "video": "videos/synthetic_species_jitter.mp4",
        "source_sha256": "0" * 64,
        "decoded_frames": N_ANCHORS * STRIDE,
        "sampled_frames": N_ANCHORS,
        "fingerprint": {"weights_sha256": "test"},
        "sample_stride": STRIDE,
        "anchors": anchors,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class AssociationModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture_root = ROOT / "results/tests"
        fixture_root.mkdir(parents=True, exist_ok=True)
        cls._tmp = tempfile.TemporaryDirectory(dir=fixture_root)
        cls.cache = Path(cls._tmp.name) / "synthetic_species_jitter.json"
        write_synthetic_cache(cls.cache)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_single_stream_keeps_one_track_across_species_jitter(self) -> None:
        """单流：物种标签抖动不得把同一目标拆成两条轨迹。"""
        payload = track_video(self.cache, DEFAULT_PARAMS, association="single")
        confirmed = [t for t in payload["tracks"] if t["state"] == "confirmed"]
        self.assertEqual(len(confirmed), 1, f"应为 1 条轨迹，实际 {len(confirmed)}：{confirmed}")
        track = confirmed[0]
        self.assertEqual(track["species"], "cat")
        # 17/20 锚点为 cat，3 个抖动锚点被多数投票吸收
        self.assertAlmostEqual(track["species_consistency"], 17 / 20, places=4)
        self.assertFalse(track["species_flagged"])

    def test_species_split_breaks_identity(self) -> None:
        """反证：硬分实例下同一目标会被拆成两条轨迹（3.2 之前的实测行为）。"""
        payload = track_video(self.cache, DEFAULT_PARAMS, association="species_split")
        confirmed = [t for t in payload["tracks"] if t["state"] == "confirmed"]
        self.assertEqual(len(confirmed), 2,
                         f"硬分实例应断裂成 2 条，实际 {len(confirmed)}")
        self.assertEqual({t["species"] for t in confirmed}, {"cat", "dog"})


if __name__ == "__main__":
    unittest.main()
