#!/usr/bin/env python3
"""Tests for cat crop geometry, target validity and paired indexes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from petlib.datasets.cat_crop import (  # noqa: E402
    build_frame_track,
    classify_frame,
    crop_bounds,
    interval_status,
    motion_correct_box,
)
import prepare_cat_crop_experiment as prepare  # noqa: E402
import run_cat_crop_experiment as runner  # noqa: E402


def detection(label: str, box: list[float], score: float) -> dict:
    return {"class": label, "box": box, "confidence": score}


def state(box: list[float] | None, reasons: list[str] | None = None) -> dict:
    reasons = reasons or ([] if box else ["no_reliable_cat_detection"])
    return {
        "cat_box": box,
        "cat_count": 1 if box else 0,
        "dog_count": 1 if "dog_present_target_ambiguous" in reasons else 0,
        "reasons": reasons,
        "target_valid": not reasons,
    }


class TargetValidityTests(unittest.TestCase):
    def test_single_cat_is_valid(self) -> None:
        result = classify_frame([detection("cat", [10, 20, 80, 100], 0.9)], 200, 120)
        self.assertTrue(result["target_valid"])
        self.assertEqual(result["cat_count"], 1)
        self.assertEqual(result["reasons"], [])

    def test_duplicate_cat_is_deduplicated(self) -> None:
        result = classify_frame(
            [
                detection("cat", [10, 20, 80, 100], 0.9),
                detection("cat", [11, 21, 81, 101], 0.8),
            ],
            200,
            120,
        )
        self.assertTrue(result["target_valid"])
        self.assertEqual(result["cat_count"], 1)

    def test_multi_cat_and_dog_are_ambiguous(self) -> None:
        cats = classify_frame(
            [
                detection("cat", [10, 20, 80, 100], 0.9),
                detection("cat", [120, 20, 190, 100], 0.8),
            ],
            200,
            120,
        )
        self.assertIn("multi_cat_target_ambiguous", cats["reasons"])
        dog = classify_frame(
            [
                detection("cat", [10, 20, 80, 100], 0.9),
                detection("dog", [120, 20, 190, 100], 0.8),
            ],
            200,
            120,
        )
        self.assertIn("dog_present_target_ambiguous", dog["reasons"])

    def test_no_cat_is_detection_missing_not_confirmed_absence(self) -> None:
        result = classify_frame([], 200, 120)
        self.assertEqual(result["reasons"], ["no_reliable_cat_detection"])
        self.assertFalse(result["target_valid"])

    def test_edge_boxes_and_crop_are_clipped(self) -> None:
        left, top, right, bottom = crop_bounds(
            [-20, -10, 40, 50], frame_width=100, frame_height=80
        )
        self.assertEqual(left, 0)
        self.assertEqual(top, 0)
        self.assertGreater(right, left)
        self.assertGreater(bottom, top)


class TrackTests(unittest.TestCase):
    def test_short_gap_interpolates_and_long_gap_does_not(self) -> None:
        anchors = {
            0: state([0, 0, 10, 10]),
            10: state([10, 0, 20, 10]),
            40: state([40, 0, 50, 10]),
        }
        track = build_frame_track(anchors, 50, sample_stride=10, max_gap=20)
        self.assertTrue(track[5]["valid"])
        self.assertAlmostEqual(track[5]["camera_box"][0], 5)
        self.assertFalse(track[25]["valid"])
        self.assertFalse(track[45]["valid"])

    def test_single_missing_detection_is_interpolated(self) -> None:
        anchors = {
            0: state([0, 0, 10, 10]),
            10: state(None),
            20: state([20, 0, 30, 10]),
        }
        track = build_frame_track(anchors, 30, sample_stride=10, max_gap=20)
        self.assertTrue(track[0]["valid"])
        self.assertTrue(track[5]["valid"])
        self.assertTrue(track[10]["valid"])
        self.assertTrue(track[10]["missing_detection_bridged"])
        self.assertFalse(track[25]["valid"])

    def test_ambiguous_anchor_breaks_interpolation(self) -> None:
        anchors = {
            0: state([0, 0, 10, 10]),
            10: state([10, 0, 20, 10], ["multi_cat_target_ambiguous"]),
            20: state([20, 0, 30, 10]),
        }
        track = build_frame_track(anchors, 30, sample_stride=10, max_gap=20)
        self.assertTrue(track[0]["valid"])
        self.assertFalse(track[5]["valid"])
        self.assertFalse(track[10]["valid"])
        self.assertFalse(track[15]["valid"])

    def test_interval_requires_every_frame(self) -> None:
        track = [
            {"valid": True, "reason": None},
            {"valid": False, "reason": "dog_present_target_ambiguous"},
            {"valid": True, "reason": None},
        ]
        result = interval_status(1, 3, track)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "dog_present_target_ambiguous")
        self.assertEqual(result["invalid_frames"], 1)

    def test_static_pet_keeps_box_and_motion_only_expands_after_two_hits(self) -> None:
        foreground = np.zeros((80, 100), dtype=np.uint8)
        first, corrected, hit = motion_correct_box(
            foreground, [10, 10, 40, 50], previous_hit=False
        )
        self.assertEqual(first, [10.0, 10.0, 40.0, 50.0])
        self.assertFalse(corrected)
        self.assertFalse(hit)
        cv2.rectangle(foreground, (12, 12), (45, 55), 255, -1)
        second, corrected, hit = motion_correct_box(
            foreground, [10, 10, 40, 50], previous_hit=True
        )
        self.assertTrue(hit)
        self.assertTrue(corrected)
        self.assertGreater(second[2], 40)


class CacheAndIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (ROOT / "results/tests").mkdir(parents=True, exist_ok=True)

    def test_cache_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            path = Path(name) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": prepare.CACHE_SCHEMA,
                        "source_path": "/old.mp4",
                        "source_sha256": "old",
                        "fingerprint": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                prepare.load_reusable_detection(path, Path("/new.mp4"), "new", {})

    def test_paired_index_rejects_different_samples(self) -> None:
        old_root = runner.INDEX_ROOT
        try:
            with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
                root = Path(name)
                runner.INDEX_ROOT = root
                manifest = {
                    "classes": runner.CLASSES,
                    "arms": list(runner.ARMS),
                    "common_sample_set": True,
                    "training_ready": True,
                }
                (root / "manifest.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
                for split in runner.SPLITS:
                    for arm in runner.ARMS:
                        sample_id = "same" if arm != "gdino_motion" else "different"
                        row = {
                            "sample_id": sample_id,
                            "label": 0,
                            "start_frame": 1,
                            "end_frame": 10,
                            "video": "v.mp4",
                        }
                        (root / f"{arm}_{split}.jsonl").write_text(
                            json.dumps(row) + "\n", encoding="utf-8"
                        )
                with self.assertRaises(ValueError):
                    runner.validate_common_indexes()
        finally:
            runner.INDEX_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
