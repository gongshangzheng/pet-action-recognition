#!/usr/bin/env python3
"""Tests for cat crop geometry, target validity and paired indexes."""

from __future__ import annotations

import csv
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/checks"))

from petlib.datasets.cat_crop import (  # noqa: E402
    build_frame_track,
    classify_frame,
    crop_bounds,
    crop_square,
    interval_status,
    letterbox_square,
    motion_correct_box,
)
from petlib.followcam import (  # noqa: E402
    DEFAULT_MOVING_AVERAGE_WINDOW,
    MotionOffsetSmoother,
    centered_moving_average,
    cosine_anchor_weight,
)
import build_cat_crop_qc_sheets as qc  # noqa: E402
import check_cat_crop_experiment as crop_check  # noqa: E402
import prepare_cat_crop_experiment as prepare  # noqa: E402
import run_cat_crop_experiment as runner  # noqa: E402
import select_cat_crop_quality_sample as quality  # noqa: E402
from petlib import videowriter  # noqa: E402


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
        self.assertEqual(result["target_class"], "cat")
        self.assertEqual(result["reasons"], [])

    def test_single_dog_is_valid_and_labeled(self) -> None:
        result = classify_frame([detection("dog", [10, 20, 90, 110], 0.9)], 200, 120)
        self.assertTrue(result["target_valid"])
        self.assertEqual(result["dog_count"], 1)
        self.assertEqual(result["target_class"], "dog")
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

    def test_multi_pets_are_unsupported(self) -> None:
        cats = classify_frame(
            [
                detection("cat", [10, 20, 80, 100], 0.9),
                detection("cat", [120, 20, 190, 100], 0.8),
            ],
            200,
            120,
        )
        self.assertIn("multi_pet_unsupported", cats["reasons"])
        dog = classify_frame(
            [
                detection("cat", [10, 20, 80, 100], 0.9),
                detection("dog", [120, 20, 190, 100], 0.8),
            ],
            200,
            120,
        )
        self.assertIn("multi_pet_unsupported", dog["reasons"])

    def test_no_pet_is_detection_missing_not_confirmed_absence(self) -> None:
        result = classify_frame([], 200, 120)
        self.assertEqual(result["reasons"], ["no_reliable_pet_detection"])
        self.assertFalse(result["target_valid"])

    def test_edge_boxes_use_a_padded_square_window(self) -> None:
        left, top, right, bottom = crop_bounds(
            [-20, -10, 40, 50],
            frame_width=100,
            frame_height=80,
            pad=1.0,
        )
        self.assertEqual((left, top, right, bottom), (-20, -10, 40, 50))
        self.assertEqual(right - left, bottom - top)

    def test_crop_square_pads_without_shifting_target_inward(self) -> None:
        frame = np.full((80, 100, 3), 200, dtype=np.uint8)
        result = crop_square(
            frame,
            [-20, -10, 40, 50],
            size=60,
            pad=1.0,
            background=7,
        )
        self.assertEqual(result.shape, (60, 60, 3))
        self.assertTrue(np.all(result[:10, :20] == 7))
        self.assertTrue(np.all(result[10:, 20:] == 200))

    def test_wide_requested_square_is_not_capped_to_frame_minimum(self) -> None:
        left, top, right, bottom = crop_bounds(
            [20, 0, 170, 100],
            frame_width=200,
            frame_height=100,
            pad=1.0,
        )
        self.assertEqual((right - left, bottom - top), (150, 150))
        self.assertGreater(right - left, min(200, 100))
        self.assertLess(top, 0)
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        frame[:, 20:170] = 255
        result = crop_square(
            frame,
            [20, 0, 170, 100],
            size=150,
            pad=1.0,
            background=7,
        )
        self.assertEqual(int(result[75, 0, 0]), 255)
        self.assertEqual(int(result[75, 149, 0]), 255)

    def test_letterbox_fallback_keeps_non_square_source_content(self) -> None:
        frame = np.zeros((40, 80, 3), dtype=np.uint8)
        frame[10:30, 20:60] = (20, 120, 220)
        result = letterbox_square(frame, 64)
        self.assertEqual(result.shape, (64, 64, 3))
        self.assertGreater(int(result.max()), 32)


class TrackTests(unittest.TestCase):
    def test_display_uses_centered_moving_average_without_changing_training_box(
        self,
    ) -> None:
        anchors = {0: state([0, 0, 10, 10]), 10: state([100, 0, 110, 10])}
        track = build_frame_track(anchors, 11, sample_stride=10, max_gap=20)
        self.assertAlmostEqual(track[2]["display_box"][0], 20.0)
        self.assertAlmostEqual(track[2]["camera_box"][0], 20)
        self.assertEqual(
            track[2]["display_smoothing"],
            f"centered-moving-average-{DEFAULT_MOVING_AVERAGE_WINDOW}-"
            "edge-padded-v1",
        )

    def test_display_track_is_continuous_through_missing_and_long_gaps(
        self,
    ) -> None:
        anchors = {
            0: state([10, 20, 30, 40]),
            10: state(None),
            40: state([50, 20, 70, 40]),
        }
        track = build_frame_track(anchors, 50, sample_stride=10, max_gap=20)
        self.assertTrue(all(record["display_box"] is not None for record in track))
        self.assertFalse(track[10]["valid"])
        self.assertFalse(track[25]["valid"])
        self.assertTrue(track[25]["display_long_gap"])
        self.assertIsNone(track[25]["camera_box"])

    def test_centered_average_edge_padding_does_not_pull_static_box_to_zero(
        self,
    ) -> None:
        boxes = np.tile(np.array([[10.0, 20.0, 30.0, 40.0]]), (7, 1))
        smoothed = centered_moving_average(
            boxes, window_size=DEFAULT_MOVING_AVERAGE_WINDOW
        )
        np.testing.assert_allclose(smoothed, boxes)

    def test_centered_average_requires_an_odd_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive odd"):
            centered_moving_average([[0.0, 1.0]], window_size=4)

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

    def test_single_dog_track_preserves_species(self) -> None:
        anchors = {
            0: {
                "target_box": [0, 0, 10, 10],
                "target_class": "dog",
                "dog_count": 1,
                "cat_count": 0,
                "pet_count": 1,
                "reasons": [],
                "target_valid": True,
            }
        }
        track = build_frame_track(anchors, 11, sample_stride=10, max_gap=20)
        self.assertTrue(track[0]["valid"])
        self.assertEqual(track[0]["target_class"], "dog")

    def test_species_change_breaks_interpolation(self) -> None:
        anchors = {
            0: {
                "target_box": [0, 0, 10, 10],
                "target_class": "cat",
                "cat_count": 1,
                "dog_count": 0,
                "pet_count": 1,
                "reasons": [],
                "target_valid": True,
            },
            20: {
                "target_box": [20, 0, 30, 10],
                "target_class": "dog",
                "cat_count": 0,
                "dog_count": 1,
                "pet_count": 1,
                "reasons": [],
                "target_valid": True,
            },
        }
        track = build_frame_track(anchors, 21, sample_stride=10, max_gap=20)
        self.assertTrue(track[0]["valid"])
        self.assertTrue(track[20]["valid"])
        for record in track[1:20]:
            self.assertFalse(record["valid"])
        self.assertTrue(all(record.get("display_box") is not None for record in track))
        self.assertLess(track[20]["display_box"][0], 20)
        self.assertIsNone(track[10]["camera_box"])

    def test_long_detection_gap_keeps_display_crop(self) -> None:
        anchors = {
            0: state([0, 0, 10, 10]),
            40: state([40, 0, 50, 10]),
        }
        track = build_frame_track(anchors, 50, sample_stride=10, max_gap=20)
        self.assertIsNone(track[20]["camera_box"])
        self.assertIsNotNone(track[20]["display_box"])
        self.assertTrue(track[20]["display_long_gap"])
        self.assertIsNotNone(track[45]["display_box"])

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
            10: state([10, 0, 20, 10], ["multi_pet_unsupported"]),
            20: state([20, 0, 30, 10]),
        }
        track = build_frame_track(anchors, 30, sample_stride=10, max_gap=20)
        self.assertTrue(track[0]["valid"])
        self.assertFalse(track[5]["valid"])
        self.assertFalse(track[10]["valid"])
        self.assertFalse(track[15]["valid"])
        self.assertIsNotNone(track[5]["display_box"])
        self.assertIsNotNone(track[10]["display_box"])
        self.assertIsNone(track[5]["camera_box"])

    def test_interval_requires_every_frame(self) -> None:
        track = [
            {"valid": True, "reason": None},
            {"valid": False, "reason": "multi_pet_unsupported"},
            {"valid": True, "reason": None},
        ]
        result = interval_status(1, 3, track)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "multi_pet_unsupported")
        self.assertEqual(result["invalid_frames"], 1)

    def test_interval_rejects_species_change(self) -> None:
        track = [
            {"valid": True, "reason": None, "target_class": "cat"},
            {"valid": True, "reason": None, "target_class": None},
            {"valid": True, "reason": None, "target_class": "dog"},
        ]
        result = interval_status(1, 3, track)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "target_species_changed")

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


class FollowCameraTests(unittest.TestCase):
    def test_valid_and_invalid_render_same_base_camera(self) -> None:
        args = argparse.Namespace(size=64, pad=1.2)
        frame = np.zeros((80, 100, 3), dtype=np.uint8)
        valid = {"valid": True, "display_box": [10, 10, 40, 40]}
        invalid = {"valid": False, "display_box": [10, 10, 40, 40]}
        rendered = np.ones((64, 64, 3), dtype=np.uint8)
        with mock.patch.object(
            prepare, "crop_square", return_value=rendered
        ) as crop:
            valid_crop, valid_box = prepare.render_base_crop(frame, valid, args)
            invalid_crop, invalid_box = prepare.render_base_crop(frame, invalid, args)
        self.assertIs(valid_crop, rendered)
        self.assertIs(invalid_crop, rendered)
        self.assertEqual(valid_box, invalid_box)
        self.assertEqual(crop.call_count, 2)

    def test_streaming_render_keeps_display_camera_and_advances_offset_state(
        self,
    ) -> None:
        fixture_root = ROOT / "results/tests"
        fixture_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_root) as name:
            root = Path(name)
            paths = {
                "gdino": root / "videos/gdino/v.mp4",
                "gdino_motion": root / "videos/gdino_motion/v.mp4",
                "metadata": root / "metadata/v.json",
            }
            frame = np.zeros((80, 100, 3), dtype=np.uint8)
            track = [
                {"valid": True, "display_box": [0, 0, 20, 20]},
                {
                    "valid": False,
                    "display_box": [10, 0, 30, 20],
                    "reason": "multi_pet_unsupported",
                },
                {"valid": True, "display_box": [20, 0, 40, 20]},
            ]
            detection = {
                "source_sha256": "digest",
                "fingerprint": {"detector": "frozen"},
                "decoded_frames": 3,
                "anchors": {"0": {}, "10": {}},
            }

            class FakeCapture:
                def __init__(self, _path: str) -> None:
                    self.remaining = 3

                def isOpened(self) -> bool:
                    return True

                def get(self, prop: int) -> float:
                    if prop == cv2.CAP_PROP_FPS:
                        return 10.0
                    if prop == cv2.CAP_PROP_FRAME_WIDTH:
                        return 100.0
                    return 0.0

                def read(self):
                    if self.remaining == 0:
                        return False, None
                    self.remaining -= 1
                    return True, frame.copy()

                def release(self) -> None:
                    pass

            background = mock.Mock()
            background.apply.return_value = np.zeros((80, 100), dtype=np.uint8)
            smoother = mock.Mock()
            smoother.update.side_effect = (
                lambda frame_index, base_box, assisted_box, previous, following: (
                    base_box,
                    np.zeros(4),
                )
            )
            writers = [mock.MagicMock(), mock.MagicMock()]
            for writer in writers:
                writer.__enter__.return_value = writer
                writer.__exit__.return_value = False
            args = argparse.Namespace(
                force=True,
                size=64,
                pad=1.2,
                sample_stride=10,
                max_gap=20,
                bg_lr=0.002,
                bg_warmup_frames=15,
                min_motion_coverage=0.2,
                max_motion_expansion=0.25,
                off_alpha=0.6,
                off_max_v=0.05,
                off_alpha_size=0.15,
                off_max_v_size=0.02,
                crf=23,
                ffmpeg_threads=1,
            )
            rendered = np.zeros((64, 64, 3), dtype=np.uint8)
            with (
                mock.patch.object(prepare, "load_detection", return_value=detection),
                mock.patch.object(prepare, "cache_paths", return_value=paths),
                mock.patch.object(prepare, "build_frame_track", return_value=track),
                mock.patch.object(prepare.cv2, "VideoCapture", FakeCapture),
                mock.patch.object(
                    prepare.cv2,
                    "createBackgroundSubtractorMOG2",
                    return_value=background,
                ),
                mock.patch.object(prepare, "crop_square", return_value=rendered),
                mock.patch.object(prepare, "letterbox_square") as letterbox,
                mock.patch.object(
                    prepare, "MotionOffsetSmoother", return_value=smoother
                ),
                mock.patch.object(
                    prepare, "H264VideoWriter", side_effect=writers
                ),
                mock.patch.object(prepare, "sha256", return_value="digest"),
                mock.patch.object(prepare, "atomic_json"),
                mock.patch.object(prepare.os, "replace"),
            ):
                metadata = prepare.render_video(
                    "v.mp4", Path("/videos"), root, args
                )

        self.assertEqual(metadata["frames"], 3)
        self.assertEqual(metadata["invalid_frames"], 1)
        letterbox.assert_not_called()
        self.assertEqual(
            [call.args[0] for call in smoother.update.call_args_list],
            [0, 1, 2],
        )
        self.assertEqual(writers[0].write.call_count, 3)
        self.assertEqual(writers[1].write.call_count, 3)

    def test_cosine_window_zeroes_at_anchors_and_peaks_in_gap(self) -> None:
        self.assertEqual(cosine_anchor_weight(0, 0, 10, 5), 0.0)
        self.assertEqual(cosine_anchor_weight(5, 0, 10, 5), 1.0)
        self.assertEqual(cosine_anchor_weight(10, 0, 10, 5), 0.0)

    def test_motion_offset_returns_smoothly_and_resets_at_next_anchor(self) -> None:
        smoother = MotionOffsetSmoother(frame_width=100, sample_stride=10)
        base = np.array([10.0, 10.0, 40.0, 50.0])
        assisted = base + np.array([20.0, 16.0, 10.0, 8.0])
        peak = 0.0
        for frame in range(1, 6):
            _, offset = smoother.update(frame, base, assisted, 0, 10)
            peak = max(peak, abs(offset[0]))
        returning = []
        for frame in range(6, 10):
            _, offset = smoother.update(frame, base, base, 0, 10)
            returning.append(abs(offset[0]))
        self.assertGreater(peak, 0)
        self.assertLess(returning[-1], returning[0])
        camera, offset = smoother.update(10, base, base, 0, 10)
        np.testing.assert_allclose(camera, base)
        np.testing.assert_allclose(offset, np.zeros(4))

    def test_motion_offset_honors_legacy_xyxy_channel_velocity_limits(
        self,
    ) -> None:
        smoother = MotionOffsetSmoother(frame_width=200, sample_stride=10)
        base = [0.0, 0.0, 20.0, 20.0]
        assisted = [100.0, 100.0, 120.0, 120.0]
        _, offset = smoother.update(5, base, assisted, 0, 10)
        self.assertLessEqual(abs(offset[0]), 0.6 * 0.05 * 200 + 1e-9)
        self.assertLessEqual(abs(offset[2]), 0.15 * 0.02 * 200 + 1e-9)

    def test_square_crop_bounds_extend_past_frame_edges(self) -> None:
        left, top, right, bottom = crop_bounds(
            [-20, -10, 20, 30],
            frame_width=100,
            frame_height=80,
            pad=1.0,
        )
        self.assertEqual((left, top, right, bottom), (-20, -10, 20, 30))
        self.assertEqual(right - left, bottom - top)


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

    def test_source_roots_are_required(self) -> None:
        args = argparse.Namespace(
            index_root=None,
            video_root=None,
            sample_stride=10,
            max_gap=20,
            size=512,
            pad=1.2,
            bg_warmup_frames=15,
            off_alpha=0.6,
            off_max_v=0.05,
            off_alpha_size=0.15,
            off_max_v_size=0.02,
            torch_threads=1,
            opencv_threads=1,
            ffmpeg_threads=1,
            crf=23,
        )
        with self.assertRaisesRegex(ValueError, "index-root"):
            prepare.validate_args(args)

    def test_mismatched_render_outputs_are_not_reused(self) -> None:
        args = argparse.Namespace(force=False)
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            root = Path(name)
            source = root / "videos/v.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            detection = {
                "fingerprint": {"new": True},
                "source_sha256": prepare.sha256(source),
            }
            paths = {
                "gdino": root / "gdino.mp4",
                "gdino_motion": root / "motion.mp4",
                "metadata": root / "metadata.json",
            }
            for path in paths.values():
                path.write_text("{}", encoding="utf-8")
            with (
                mock.patch.object(prepare, "load_detection", return_value=detection),
                mock.patch.object(prepare, "cache_paths", return_value=paths),
            ):
                with self.assertRaisesRegex(RuntimeError, "do not match"):
                    prepare.render_video(
                        "v.mp4", source.parent, root, args
                    )

    def test_render_video_rejects_stale_detection_source_hash_before_read(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            root = Path(name)
            source = root / "videos/v.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"current source")
            detection = {
                "source_sha256": "stale",
                "fingerprint": {"detector": "frozen"},
                "status": "complete",
            }
            with (
                mock.patch.object(prepare, "load_detection", return_value=detection),
                mock.patch.object(prepare.cv2, "VideoCapture") as capture,
                self.assertRaisesRegex(RuntimeError, "source hash"),
            ):
                prepare.render_video(
                    "v.mp4",
                    root / "videos",
                    root / "assets",
                    argparse.Namespace(force=False),
                )
            capture.assert_not_called()

    def test_index_build_rejects_cached_metadata_with_missing_media(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            root = Path(name)
            video_root = root / "sources"
            asset_root = root / "assets"
            dataset_root = root / "dataset"
            video = "videos/v.mp4"
            source = video_root / video
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            paths = prepare.cache_paths(asset_root, video)
            for path in (paths["detection"], paths["metadata"], paths["gdino"]):
                path.parent.mkdir(parents=True, exist_ok=True)
            paths["detection"].write_text(
                json.dumps(
                    {
                        "schema": prepare.CACHE_SCHEMA,
                        "status": "complete",
                        "source_sha256": prepare.sha256(source),
                        "fingerprint": {"detector": "current"},
                    }
                ),
                encoding="utf-8",
            )
            paths["gdino"].write_bytes(b"gdino")
            args = argparse.Namespace(
                index_root=root / "index",
                video_root=video_root,
                dataset_root=dataset_root,
                dataset_id="test",
                video=[video],
                max_videos=1,
                sample_stride=10,
                max_gap=20,
                size=512,
                pad=1.2,
                bg_lr=0.002,
                bg_warmup_frames=15,
                min_motion_coverage=0.2,
                max_motion_expansion=0.25,
                off_alpha=0.6,
                off_max_v=0.05,
                off_alpha_size=0.15,
                off_max_v_size=0.02,
                crf=23,
                ffmpeg_threads=1,
                force=True,
                model_dir="/unused",
                threshold=0.3,
                text_threshold=0.3,
            )
            paths["metadata"].write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "source_sha256": prepare.sha256(source),
                        "detection_fingerprint": {"detector": "current"},
                        "render_fingerprint": prepare.render_fingerprint(args),
                        "gdino_video": str(paths["gdino"]),
                        "gdino_video_sha256": prepare.sha256(paths["gdino"]),
                        "gdino_motion_video": str(paths["gdino_motion"]),
                        "gdino_motion_video_sha256": "missing",
                        "track": [{"valid": True} for _ in range(3)],
                    }
                ),
                encoding="utf-8",
            )
            rows = [
                {
                    "video": video,
                    "sample_id": "sample",
                    "task_id": "task",
                    "split": "train",
                    "start_frame": 1,
                    "end_frame": 3,
                    "label": 0,
                }
            ]
            with mock.patch.object(
                prepare,
                "detection_fingerprint_for_args",
                return_value={"detector": "current"},
            ):
                manifest = prepare.build_indexes(
                    rows, asset_root, dataset_root, args
                )
                gdino_train = (dataset_root / "gdino_train.jsonl").read_text()

        self.assertEqual(manifest["eligible_rows"], 0)
        self.assertEqual(
            manifest["availability"]["train"]["unavailable_reasons"],
            {"crop_media_missing": 1},
        )
        self.assertEqual(gdino_train, "")

    def test_index_asset_gate_rejects_each_stale_dependency(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            root = Path(name)
            video = "videos/v.mp4"
            video_root = root / "sources"
            asset_root = root / "assets"
            source = video_root / video
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            paths = prepare.cache_paths(asset_root, video)
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
            paths["detection"].write_bytes(b"detection")
            paths["gdino"].write_bytes(b"gdino")
            paths["gdino_motion"].write_bytes(b"motion")

            expected_detection = {"detector": "current"}
            expected_render = {"render": "current"}

            def write_valid_metadata() -> None:
                paths["detection"].write_text(
                    json.dumps(
                        {
                            "schema": prepare.CACHE_SCHEMA,
                            "status": "complete",
                            "source_sha256": prepare.sha256(source),
                            "fingerprint": expected_detection,
                        }
                    ),
                    encoding="utf-8",
                )
                paths["metadata"].write_text(
                    json.dumps(
                        {
                            "status": "complete",
                            "source_sha256": prepare.sha256(source),
                            "detection_fingerprint": expected_detection,
                            "render_fingerprint": expected_render,
                            "gdino_video": str(paths["gdino"]),
                            "gdino_video_sha256": prepare.sha256(paths["gdino"]),
                            "gdino_motion_video": str(paths["gdino_motion"]),
                            "gdino_motion_video_sha256": prepare.sha256(
                                paths["gdino_motion"]
                            ),
                            "track": [{"valid": True}],
                        }
                    ),
                    encoding="utf-8",
                )

            write_valid_metadata()
            valid = prepare.validate_index_assets(
                video,
                asset_root,
                video_root,
                expected_detection,
                expected_render,
            )
            self.assertTrue(valid["ready"])

            mutations = (
                (
                    "source_hash_mismatch",
                    lambda: source.write_bytes(b"changed source"),
                    write_valid_metadata,
                ),
                (
                    "detection_fingerprint_mismatch",
                    lambda: paths["detection"].write_text(
                        json.dumps(
                            {
                                "schema": prepare.CACHE_SCHEMA,
                                "status": "complete",
                                "source_sha256": prepare.sha256(source),
                                "fingerprint": {"detector": "stale"},
                            }
                        ),
                        encoding="utf-8",
                    ),
                    write_valid_metadata,
                ),
                (
                    "render_fingerprint_mismatch",
                    lambda: None,
                    write_valid_metadata,
                ),
                (
                    "crop_media_hash_mismatch",
                    lambda: paths["gdino_motion"].write_bytes(b"changed"),
                    write_valid_metadata,
                ),
                (
                    "crop_media_missing",
                    paths["gdino_motion"].unlink,
                    write_valid_metadata,
                ),
            )
            for expected_reason, mutate, restore in mutations:
                with self.subTest(reason=expected_reason):
                    write_valid_metadata()
                    mutate()
                    render_fingerprint = (
                        {"render": "stale"}
                        if expected_reason == "render_fingerprint_mismatch"
                        else expected_render
                    )
                    result = prepare.validate_index_assets(
                        video,
                        asset_root,
                        video_root,
                        expected_detection,
                        render_fingerprint,
                    )
                    self.assertFalse(result["ready"])
                    self.assertEqual(result["reason"], expected_reason)
                    motion_path = paths["gdino_motion"]
                    motion_path.parent.mkdir(parents=True, exist_ok=True)
                    motion_path.write_bytes(b"motion")
                    restore()

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


class VideoWriterTests(unittest.TestCase):
    def test_ffmpeg_default_command_omits_thread_limit(self) -> None:
        process = mock.Mock()
        with (
            mock.patch.object(videowriter, "_find_ffmpeg", return_value="/bin/ffmpeg"),
            mock.patch.object(
                videowriter.subprocess, "Popen", return_value=process
            ) as popen,
        ):
            videowriter.H264VideoWriter("/tmp/out.mp4", fps=10, size=(32, 32))
            command = popen.call_args.args[0]
        self.assertNotIn("-threads", command)

    def test_ffmpeg_thread_limit_is_passed_when_explicit(self) -> None:
        process = mock.Mock()
        with (
            mock.patch.object(videowriter, "_find_ffmpeg", return_value="/bin/ffmpeg"),
            mock.patch.object(
                videowriter.subprocess, "Popen", return_value=process
            ) as popen,
        ):
            writer = videowriter.H264VideoWriter(
                "/tmp/out.mp4", fps=10, size=(32, 32), threads=2
            )
            command = popen.call_args.args[0]
        self.assertEqual(
            command[-5:],
            ["-threads", "2", "-movflags", "+faststart", "/tmp/out.mp4"],
        )
        self.assertIs(writer._proc, process)

    def test_ffmpeg_thread_limit_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "threads must be positive"):
            videowriter.H264VideoWriter(
                "/tmp/out.mp4", fps=10, size=(32, 32), threads=0
            )

    def test_render_fingerprint_tracks_ffmpeg_threads(self) -> None:
        args = mock.Mock(
            size=512,
            pad=1.2,
            sample_stride=10,
            max_gap=20,
            bg_lr=0.002,
            bg_warmup_frames=15,
            min_motion_coverage=0.2,
            max_motion_expansion=0.25,
            off_alpha=0.6,
            off_max_v=0.05,
            off_alpha_size=0.15,
            off_max_v_size=0.02,
            crf=23,
            ffmpeg_threads=1,
        )
        fingerprint = prepare.render_fingerprint(args)
        self.assertEqual(fingerprint["ffmpeg_threads"], 1)
        self.assertEqual(fingerprint["off_alpha"], 0.6)
        self.assertEqual(fingerprint["off_max_v"], 0.05)
        self.assertIn(
            "centered-ma-5-edge-padded", fingerprint["display_track"]
        )
        self.assertEqual(
            fingerprint["square_crop"],
            "padded-square-preserve-source-aspect-v3",
        )
        self.assertIn("legacy-xyxy", fingerprint["motion_offset"])
        self.assertNotIn("smooth_review", fingerprint)

    def test_opencv_threads_are_applied_before_render(self) -> None:
        args = mock.Mock(opencv_threads=2)
        with mock.patch.object(prepare.cv2, "setNumThreads") as set_threads:
            prepare.configure_opencv_threads(args)
        set_threads.assert_called_once_with(2)


class QualitySelectionTests(unittest.TestCase):
    @staticmethod
    def rows() -> list[dict]:
        rows = []
        for label in range(len(quality.CLASSES)):
            for index in range(5):
                hour = (22, 23, 10, 11, 12)[index]
                rows.append(
                    {
                        "video": (
                            f"videos/event_202606{label + 1:02d}_"
                            f"{hour:02d}00{index:02d}.mp4"
                        ),
                        "sample_id": f"{label}-{index}",
                        "start_frame": 1,
                        "end_frame": 20 + label * 10 + index,
                        "label": label,
                    }
                )
        return rows

    def test_selection_is_class_balanced_unique_and_deterministic(self) -> None:
        rows = self.rows()
        first = quality.select_quality_rows(rows, salt="fixed")
        second = quality.select_quality_rows(reversed(rows), salt="fixed")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)
        self.assertEqual(len({row["video"] for row in first}), 20)
        class_counts = {
            class_name: sum(row["class_name"] == class_name for row in first)
            for class_name in quality.CLASSES
        }
        self.assertTrue(all(count >= 2 for count in class_counts.values()))
        self.assertEqual(sum(class_counts.values()), 20)
        reason_counts = {
            reason: sum(
                row["selection_reasons"] == [reason]
                for row in first
            )
            for reason in (
                *(f"class_stratified:{name}" for name in quality.CLASSES),
                "shortest_duration",
                "longest_duration",
                "timestamp_night_candidate",
            )
        }
        self.assertTrue(
            all(
                reason_counts[f"class_stratified:{name}"] == 2
                for name in quality.CLASSES
            )
        )
        self.assertEqual(reason_counts["shortest_duration"], 2)
        self.assertEqual(reason_counts["longest_duration"], 2)
        self.assertEqual(reason_counts["timestamp_night_candidate"], 2)

    def test_missing_supplemental_stratum_fails_loudly(self) -> None:
        rows = [
            {
                **row,
                "video": row["video"].replace("_220", "_130").replace("_230", "_140"),
            }
            for row in self.rows()
        ]
        with self.assertRaisesRegex(
            ValueError, "insufficient unique candidates for timestamp_night_candidate"
        ):
            quality.select_quality_rows(rows)

    def test_sparse_night_rows_are_reserved_before_other_strata(self) -> None:
        rows = self.rows()
        for position, row in enumerate(rows):
            label, index = row["sample_id"].split("-")
            hour = 22 if position == 0 else 23 if position == 1 else 13
            row["video"] = (
                f"videos/event_202606{int(label) + 1:02d}_"
                f"{hour:02d}00{int(index):02d}.mp4"
            )
        selected = quality.select_quality_rows(rows, salt="0")
        self.assertEqual(
            sum(
                row["selection_reasons"] == ["timestamp_night_candidate"]
                for row in selected
            ),
            2,
        )

    def test_invalid_inputs_and_quotas_are_rejected(self) -> None:
        mutations = (
            lambda rows: rows[0].update(label=1.5),
            lambda rows: rows[0].update(start_frame=10, end_frame=5),
            lambda rows: rows[1].update(sample_id=rows[0]["sample_id"]),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                rows = self.rows()
                mutate(rows)
                with self.assertRaises(ValueError):
                    quality.select_quality_rows(rows)
        with self.assertRaisesRegex(ValueError, "supplemental quotas"):
            quality.select_quality_rows(
                self.rows(), night_count=-1
            )
        with self.assertRaisesRegex(ValueError, "target_total"):
            quality.select_quality_rows(self.rows(), target_total=19)


class QualitySheetTests(unittest.TestCase):
    def test_random_order_is_deterministic_and_complete(self) -> None:
        first = qc.review_order("sample", "salt")
        second = qc.review_order("sample", "salt")
        self.assertEqual(first, second)
        self.assertEqual(set(first), set(qc.VARIANTS))
        self.assertEqual(len(first), len(qc.VARIANTS))

    def test_synthetic_assets_produce_a_readable_sheet(self) -> None:
        fixture_root = ROOT / "results/tests"
        fixture_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_root) as name:
            root = Path(name)
            video_root = root / "videos"
            asset_root = root / "assets"
            sheets_root = root / "out/sheets"
            for path in (
                video_root / "videos",
                asset_root / "videos/gdino",
                asset_root / "videos/gdino_motion",
                asset_root / "metadata",
                sheets_root,
            ):
                path.mkdir(parents=True, exist_ok=True)
            paths = {
                "raw": video_root / "videos/v.avi",
                "gdino": asset_root / "videos/gdino/v.avi",
                "gdino_motion": asset_root / "videos/gdino_motion/v.avi",
            }
            sizes = {
                "raw": (96, 64),
                "gdino": (32, 32),
                "gdino_motion": (32, 32),
            }
            colors = {
                "raw": (0, 0, 200),
                "gdino": (0, 200, 0),
                "gdino_motion": (200, 0, 0),
            }
            for variant, path in paths.items():
                writer = cv2.VideoWriter(
                    str(path),
                    cv2.VideoWriter_fourcc(*"MJPG"),
                    10,
                    sizes[variant],
                )
                self.assertTrue(writer.isOpened())
                for frame_index in range(6):
                    frame = np.zeros(
                        (sizes[variant][1], sizes[variant][0], 3),
                        dtype=np.uint8,
                    )
                    frame[:] = colors[variant]
                    writer.write(frame)
                writer.release()
            metadata = {
                "status": "complete",
                "frames": 6,
                "size": 32,
                "fps": 10.0,
                "source_path": str(paths["raw"]),
                "source_sha256": qc.sha256(paths["raw"]),
                "gdino_video": str(paths["gdino"]),
                "gdino_video_sha256": qc.sha256(paths["gdino"]),
                "gdino_motion_video": str(paths["gdino_motion"]),
                "gdino_motion_video_sha256": qc.sha256(paths["gdino_motion"]),
                "track": [{"valid": True} for _ in range(6)],
            }
            (asset_root / "metadata/v.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            selection = {
                "rows": [
                    {
                        "video": "videos/v.avi",
                        "sample_id": "sample",
                        "start_frame": 2,
                        "end_frame": 6,
                        "label": 0,
                        "class_name": "activity",
                        "event_hour": None,
                        "selection_reasons": ["class_stratified:activity"],
                    }
                ]
            }
            selection_path = root / "selection.json"
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            prepared = qc.prepare_review_rows(
                selection["rows"], video_root, asset_root
            )
            review = qc.render_sheet(prepared[0], sheets_root, 32, "salt")
            image = cv2.imread(review["sheet"])
            self.assertIsNotNone(image)
            self.assertEqual(image.shape, (198, 96, 3))
            expected_channel = {
                "raw": 2,
                "gdino": 1,
                "gdino_motion": 0,
            }
            for column, variant in enumerate(review["hidden_column_order"]):
                pixel = image[50, column * 32 + 16]
                self.assertEqual(
                    int(np.argmax(pixel)),
                    expected_channel[variant],
                )
            qc.write_outputs(root / "out", selection_path, [review])
            with (root / "out/source.csv").open(encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 1)
            with (root / "out/review_form.csv").open(encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 1)


class AuditVideoSelectionTests(unittest.TestCase):
    def test_explicit_videos_can_be_outside_indexes_and_are_deduplicated(self) -> None:
        videos = crop_check.select_audit_videos(
            {"indexed.mp4"},
            ["other.mp4", "other.mp4", "indexed.mp4"],
            None,
        )
        self.assertEqual(videos, ["indexed.mp4", "other.mp4"])

    def test_explicit_videos_cannot_be_silently_truncated(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            crop_check.select_audit_videos({"a.mp4"}, ["b.mp4"], 1)

    def test_index_videos_honor_positive_maximum(self) -> None:
        self.assertEqual(
            crop_check.select_audit_videos({"b.mp4", "a.mp4"}, [], 1),
            ["a.mp4"],
        )
        with self.assertRaisesRegex(ValueError, "must be positive"):
            crop_check.select_audit_videos({"a.mp4"}, [], 0)


if __name__ == "__main__":
    unittest.main()
