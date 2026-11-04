#!/usr/bin/env python3
"""Regression tests for metadata-only follow-camera summaries."""

from __future__ import annotations

import contextlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

from scripts import summarize_cat_crop_camera as summary


def record(
    frame: int,
    *,
    valid: bool,
    display: list[float] | None,
    camera: list[float] | None,
    reason: str | None = None,
) -> dict:
    return {
        "frame": frame,
        "valid": valid,
        "reason": reason,
        "target_class": "cat" if valid else None,
        "display_box": display,
        "camera_box": camera,
    }


def metadata(
    video: str,
    track: list[dict],
    *,
    source: str,
    fingerprint: dict,
    corrected: int,
) -> dict:
    return {
        "status": "complete",
        "video": video,
        "source_sha256": source,
        "detection_fingerprint": fingerprint,
        "frames": len(track),
        "valid_frames": sum(item["valid"] for item in track),
        "corrected_frames": corrected,
        "track": track,
    }


def detection(source: str, fingerprint: dict) -> dict:
    return {
        "status": "complete",
        "source_sha256": source,
        "fingerprint": fingerprint,
        "anchors": {
            "0": {
                "target_valid": True,
                "target_class": "cat",
                "cat_count": 1,
                "dog_count": 0,
                "pet_count": 1,
                "reasons": [],
            },
            "10": {
                "target_valid": False,
                "target_class": "cat",
                "cat_count": 2,
                "dog_count": 0,
                "pet_count": 2,
                "reasons": ["multi_pet_unsupported"],
            },
            "20": {
                "target_valid": False,
                "target_class": None,
                "cat_count": 0,
                "dog_count": 0,
                "pet_count": 0,
                "reasons": ["no_reliable_pet_detection"],
            },
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_case(
    root: Path,
    *,
    asset_track: list[dict],
    baseline_track: list[dict],
    selected_end: int = 4,
    asset_source: str = "source",
    baseline_source: str = "source",
    asset_fingerprint: dict | None = None,
    baseline_fingerprint: dict | None = None,
) -> tuple[Path, Path, Path]:
    asset_root = root / "asset"
    baseline_root = root / "baseline"
    fingerprint = {"weights_sha256": "same", "sample_stride": 10}
    asset_fingerprint = asset_fingerprint or fingerprint
    baseline_fingerprint = baseline_fingerprint or fingerprint
    video = "videos/sample.mp4"
    write_json(
        asset_root / "metadata/sample.json",
        metadata(
            video,
            asset_track,
            source=asset_source,
            fingerprint=asset_fingerprint,
            corrected=2,
        ),
    )
    write_json(
        baseline_root / "metadata/sample.json",
        metadata(
            video,
            baseline_track,
            source=baseline_source,
            fingerprint=baseline_fingerprint,
            corrected=3,
        ),
    )
    write_json(
        asset_root / "detections/sample.json",
        detection(asset_source, asset_fingerprint),
    )
    write_json(
        baseline_root / "detections/sample.json",
        detection(baseline_source, baseline_fingerprint),
    )
    selection = root / "selection.json"
    write_json(
        selection,
        {
            "rows": [
                {
                    "sample_id": "sample-id",
                    "video": video,
                    "start_frame": 1,
                    "end_frame": selected_end,
                }
            ]
        },
    )
    return asset_root, baseline_root, selection


def run_summary(
    asset_root: Path, baseline_root: Path, selection: Path, output: Path
) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = summary.main(
            [
                "--asset-root",
                str(asset_root),
                "--baseline-root",
                str(baseline_root),
                "--selection",
                str(selection),
                "--out",
                str(output),
            ]
        )
    return result, stdout.getvalue().strip()


class CatCropCameraSummaryTests(unittest.TestCase):
    def test_counts_motion_eligibility_and_compact_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset_track = [
                record(0, valid=True, display=[0, 0, 10, 10], camera=[0, 0, 10, 10]),
                record(1, valid=True, display=[3, 0, 13, 10], camera=[3, 0, 13, 10]),
                record(
                    2,
                    valid=False,
                    display=None,
                    camera=[6, 0, 26, 10],
                    reason="multi_pet_unsupported",
                ),
                record(3, valid=True, display=[6, 0, 26, 10], camera=[10, 0, 30, 10]),
                record(
                    4,
                    valid=False,
                    display=None,
                    camera=None,
                    reason="no_reliable_pet_detection",
                ),
            ]
            baseline_track = [
                record(0, valid=True, display=None, camera=[0, 0, 10, 10]),
                record(1, valid=True, display=[1, 0, 11, 10], camera=[3, 0, 13, 10]),
                record(
                    2,
                    valid=False,
                    display=[2, 0, 22, 10],
                    camera=[6, 0, 26, 10],
                    reason="multi_pet_unsupported",
                ),
                record(3, valid=True, display=[2, 0, 22, 10], camera=[10, 0, 30, 10]),
                record(
                    4,
                    valid=False,
                    display=None,
                    camera=None,
                    reason="no_reliable_pet_detection",
                ),
            ]
            asset_root, baseline_root, selection = write_case(
                root,
                asset_track=asset_track,
                baseline_track=baseline_track,
            )
            output = root / "report.json"
            result, stdout = run_summary(
                asset_root, baseline_root, selection, output
            )

            self.assertEqual(result, 0)
            self.assertNotIn("\n", stdout)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), stdout)
            payload = json.loads(stdout)
            item = payload["videos"][0]
            self.assertEqual(item["q_id"], "Q001")
            self.assertEqual(item["asset"]["total_frames"], 5)
            self.assertEqual(item["asset"]["valid_frames"], 3)
            self.assertEqual(
                item["asset"]["display_missing_letterbox_frames"], 2
            )
            self.assertEqual(
                item["baseline"]["display_missing_letterbox_frames"], 1
            )
            self.assertEqual(
                item["asset"]["pixel_motion_frames_from_metadata"], 2
            )

            current_motion = item["asset"]["base_trajectory_motion"]
            self.assertEqual(current_motion["consecutive_box_pairs"], 1)
            self.assertFalse(current_motion["camera_box_fallback"])
            self.assertAlmostEqual(
                current_motion["normalized_center_step"]["mean"], 0.3
            )
            baseline_motion = item["baseline"]["base_trajectory_motion"]
            self.assertEqual(baseline_motion["consecutive_box_pairs"], 3)
            self.assertTrue(baseline_motion["camera_box_fallback"])
            self.assertAlmostEqual(
                baseline_motion["normalized_center_step"]["mean"],
                (0.1 + 0.4) / 3,
            )
            self.assertAlmostEqual(
                baseline_motion["abs_log_side_step"]["max"], math.log(2)
            )

            comparison = item["comparison"]
            self.assertTrue(comparison["source_sha256"]["identical"])
            self.assertTrue(comparison["detection_fingerprint"]["identical"])
            self.assertTrue(
                comparison["track_eligibility"]["eligibility_track_unchanged"]
            )
            self.assertTrue(comparison["selected_eligibility"]["unchanged"])
            counts = comparison["detection_state_counts"]["asset"]["state_counts"]
            self.assertEqual(counts["target_valid"], {"false": 2, "true": 1})
            self.assertEqual(counts["cat_count"], {"0": 1, "1": 1, "2": 1})
            self.assertFalse(payload["acceptance_thresholds_applied"])
            self.assertIn("not the actual C-arm rendered path", payload["basis_notice"])

    def test_source_fingerprint_and_track_differences_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset_root, baseline_root, selection = write_case(
                root,
                asset_track=[
                    record(
                        0, valid=True, display=[0, 0, 10, 10], camera=[0, 0, 10, 10]
                    ),
                    record(
                        1, valid=True, display=[1, 0, 11, 10], camera=[1, 0, 11, 10]
                    ),
                ],
                baseline_track=[
                    record(
                        0,
                        valid=False,
                        display=[0, 0, 10, 10],
                        camera=None,
                        reason="no_reliable_pet_detection",
                    ),
                    record(
                        1,
                        valid=False,
                        display=[1, 0, 11, 10],
                        camera=None,
                        reason="no_reliable_pet_detection",
                    ),
                ],
                asset_source="new",
                baseline_source="old",
                selected_end=2,
                asset_fingerprint={"weights_sha256": "new"},
                baseline_fingerprint={"weights_sha256": "old"},
            )
            output = root / "mismatch.json"
            result, _ = run_summary(asset_root, baseline_root, selection, output)

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            item = payload["videos"][0]
            self.assertFalse(item["comparison"]["source_sha256"]["identical"])
            self.assertFalse(
                item["comparison"]["detection_fingerprint"]["identical"]
            )
            self.assertFalse(
                item["comparison"]["track_eligibility"][
                    "eligibility_track_unchanged"
                ]
            )
            self.assertEqual(
                item["comparison"]["track_eligibility"][
                    "valid_flags_changed_frames"
                ],
                2,
            )
            self.assertTrue(
                item["comparison"]["selected_eligibility"]["asset"]["eligible"]
            )
            self.assertFalse(
                item["comparison"]["selected_eligibility"]["baseline"]["eligible"]
            )
            self.assertFalse(payload["totals"]["all_source_hashes_identical"])
            self.assertFalse(payload["acceptance_thresholds_applied"])


if __name__ == "__main__":
    unittest.main()
