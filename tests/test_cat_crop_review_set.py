import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from scripts.prepare_cat_crop_review_set import build_review_set, export_clip, probe_fps


class CatCropReviewSetTests(unittest.TestCase):
    def test_probe_fps_uses_opencv_without_ffprobe(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.avi"
            writer = cv2.VideoWriter(
                str(path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                12.0,
                (32, 24),
            )
            self.assertTrue(writer.isOpened())
            for _ in range(4):
                writer.write(np.zeros((24, 32, 3), dtype=np.uint8))
            writer.release()
            self.assertAlmostEqual(probe_fps(path), 12.0, delta=0.1)

    def test_export_preserves_one_output_frame_per_selected_source_frame(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            output = root / "output.mp4"
            with patch(
                "scripts.prepare_cat_crop_review_set.subprocess.run"
            ) as run:
                def write_temporary(command, check):
                    self.assertTrue(check)
                    Path(command[-1]).write_bytes(b"video")

                run.side_effect = write_temporary
                export_clip(
                    source=source,
                    output=output,
                    start_frame=1,
                    end_frame=181,
                    fps=10.933574136769685,
                    crf=22,
                )
            command = run.call_args.args[0]
            self.assertNotIn("-r", command)
            self.assertEqual(command[command.index("-fps_mode") + 1], "passthrough")
            filter_graph = command[command.index("-vf") + 1]
            self.assertIn(
                "setpts=N/(10.933574136770*TB)", filter_graph
            )
            self.assertTrue(output.is_file())

    def test_builds_frame_aligned_three_arm_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "sources"
            asset_root = root / "assets"
            output = root / "review"
            source = source_root / "sample.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            for arm in ("gdino", "gdino_motion"):
                path = asset_root / "videos" / arm / "sample.mp4"
                path.parent.mkdir(parents=True)
                path.write_bytes(arm.encode())

            selection = root / "selection.json"
            selection.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "sample_id": "sample-1",
                                "video": "sample.mp4",
                                "class_name": "activity",
                                "label": 0,
                                "start_frame": 11,
                                "end_frame": 40,
                                "frame_count": 30,
                                "event_hour": 8,
                                "selection_reasons": ["quota", "short"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            availability = root / "availability.json"
            availability.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "sample_id": "sample-1",
                                "available": True,
                                "invalid_frames": 0,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def fake_export(source, destination, *args):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())

            args = Namespace(
                selection=selection,
                selection_sha256="a" * 64,
                source_root=source_root,
                asset_root=asset_root,
                availability=availability,
                output=output,
                crf=22,
                force=True,
            )
            with patch(
                "scripts.prepare_cat_crop_review_set.probe_fps", return_value=25.0
            ), patch(
                "scripts.prepare_cat_crop_review_set.export_clip",
                side_effect=fake_export,
            ):
                payload = build_review_set(args)

            self.assertEqual(payload["mode"], "crop_comparison")
            self.assertEqual(payload["count"], 1)
            item = payload["items"][0]
            self.assertEqual(item["review_id"], "Q001")
            self.assertEqual(item["frame_count"], 30)
            self.assertTrue(item["strict_available"])
            self.assertEqual(
                set(item["files"]), {"raw", "gdino", "gdino_motion"}
            )
            manifest = json.loads((output / "items.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["selection_sha256"], "a" * 64)
            for relative in item["files"].values():
                self.assertTrue((output / relative).is_file())


if __name__ == "__main__":
    unittest.main()
