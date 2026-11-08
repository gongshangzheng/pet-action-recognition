import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from server.routers import gate_review


class GateCropReviewApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.set_dir = self.root / "crop-review"
        (self.set_dir / "media" / "Q001").mkdir(parents=True)
        for arm in ("raw", "gdino", "gdino_motion"):
            (self.set_dir / "media" / "Q001" / f"{arm}.mp4").write_bytes(
                f"{arm}-video".encode()
            )
        items = [
            {
                "path": f"Q{index:03d}",
                "file": f"media/Q{index:03d}/raw.mp4",
                "files": {
                    "raw": f"media/Q{index:03d}/raw.mp4",
                    "gdino": f"media/Q{index:03d}/gdino.mp4",
                    "gdino_motion": f"media/Q{index:03d}/gdino_motion.mp4",
                },
            }
            for index in (1, 2)
        ]
        (self.set_dir / "items.json").write_text(
            json.dumps({"mode": "crop_comparison", "items": items}),
            encoding="utf-8",
        )
        for index in (2,):
            item_dir = self.set_dir / "media" / f"Q{index:03d}"
            item_dir.mkdir(parents=True)
            for arm in ("raw", "gdino", "gdino_motion"):
                (item_dir / f"{arm}.mp4").write_bytes(b"video")
        self.patch = patch.object(gate_review, "REVIEW_ROOT", str(self.root))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temporary.cleanup()

    def test_crop_comparison_allows_each_declared_arm_only(self):
        for arm in ("raw", "gdino", "gdino_motion"):
            response = gate_review.video(
                "crop-review", f"media/Q001/{arm}.mp4"
            )
            self.assertEqual(response.media_type, "video/mp4")
        with self.assertRaises(HTTPException) as raised:
            gate_review.video("crop-review", "media/Q001/unlisted.mp4")
        self.assertEqual(raised.exception.status_code, 404)

    def test_pass_and_fail_are_counted_separately(self):
        gate_review.set_label(
            "crop-review",
            gate_review.LabelPayload(
                path="Q001", human_label="pass", note="body_cut"
            ),
        )
        gate_review.set_label(
            "crop-review",
            gate_review.LabelPayload(
                path="Q002", human_label="fail", note="gray_frames;wrong_target"
            ),
        )
        result = gate_review.stats("crop-review")
        self.assertEqual(result["counts"]["pass"], 1)
        self.assertEqual(result["counts"]["fail"], 1)
        self.assertEqual(result["counts"]["unlabeled"], 0)
        with (self.set_dir / "labels.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["human_label"] for row in rows], ["pass", "fail"])
        self.assertEqual(rows[1]["note"], "gray_frames;wrong_target")


if __name__ == "__main__":
    unittest.main()
