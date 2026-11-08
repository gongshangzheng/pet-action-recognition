import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from scripts.checks.check_cat_crop_review_set import audit_set, probe_video


class CatCropReviewAuditTests(unittest.TestCase):
    def test_probe_video_uses_opencv_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.avi"
            writer = cv2.VideoWriter(
                str(path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                10.0,
                (32, 24),
            )
            self.assertTrue(writer.isOpened())
            for _ in range(5):
                writer.write(np.zeros((24, 32, 3), dtype=np.uint8))
            writer.release()
            properties = probe_video(path)
            self.assertEqual(properties["frames"], 5)
            self.assertAlmostEqual(properties["fps"], 10.0, delta=0.1)
            self.assertEqual(properties["width"], 32)
            self.assertEqual(properties["height"], 24)
            self.assertAlmostEqual(properties["duration"], 0.5, delta=0.02)

    def test_audits_declared_triplet(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {}
            for arm in ("raw", "gdino", "gdino_motion"):
                relative = f"media/Q001/{arm}.mp4"
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(arm.encode())
                files[arm] = relative
            (root / "items.json").write_text(
                json.dumps(
                    {
                        "mode": "crop_comparison",
                        "items": [
                            {
                                "review_id": "Q001",
                                "sample_id": "sample-1",
                                "class_name": "activity",
                                "frame_count": 30,
                                "strict_available": True,
                                "files": files,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            properties = {
                "frames": 30,
                "fps": 25.0,
                "duration": 1.2,
                "width": 512,
                "height": 512,
            }
            with patch(
                "scripts.checks.check_cat_crop_review_set.probe_video",
                return_value=properties,
            ):
                report = audit_set(root)
            self.assertTrue(report["passed"])
            self.assertEqual(report["count"], 1)
            self.assertTrue((root / "audit.json").is_file())


if __name__ == "__main__":
    unittest.main()
