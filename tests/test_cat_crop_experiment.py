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
    interval_status,
    letterbox_square,
    motion_correct_box,
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

    def test_edge_boxes_and_crop_are_clipped(self) -> None:
        left, top, right, bottom = crop_bounds(
            [-20, -10, 40, 50], frame_width=100, frame_height=80
        )
        self.assertEqual(left, 0)
        self.assertEqual(top, 0)
        self.assertGreater(right, left)
        self.assertGreater(bottom, top)

    def test_letterbox_fallback_keeps_non_square_source_content(self) -> None:
        frame = np.zeros((40, 80, 3), dtype=np.uint8)
        frame[10:30, 20:60] = (20, 120, 220)
        result = letterbox_square(frame, 64)
        self.assertEqual(result.shape, (64, 64, 3))
        self.assertGreater(int(result.max()), 32)


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

    def test_source_roots_are_required(self) -> None:
        args = argparse.Namespace(
            index_root=None,
            video_root=None,
            sample_stride=10,
            max_gap=20,
            size=512,
            pad=1.2,
            bg_warmup_frames=15,
            torch_threads=1,
            opencv_threads=1,
            ffmpeg_threads=1,
            crf=23,
        )
        with self.assertRaisesRegex(ValueError, "index-root"):
            prepare.validate_args(args)

    def test_mismatched_render_outputs_are_not_reused(self) -> None:
        args = argparse.Namespace(force=False)
        detection = {"fingerprint": {"new": True}, "source_sha256": "new"}
        with tempfile.TemporaryDirectory(dir=ROOT / "results/tests") as name:
            root = Path(name)
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
                    prepare.render_video("v.mp4", Path("/videos"), root, args)

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
            crf=23,
            ffmpeg_threads=1,
        )
        self.assertEqual(prepare.render_fingerprint(args)["ffmpeg_threads"], 1)

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
