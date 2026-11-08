"""Raw candidates survive the real video detection path before deduplication."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_cat_crop_experiment as prepare


def test_detect_video_preserves_raw_candidates():
    test_root = ROOT / "results/tests"
    test_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=test_root) as tmp:
        root = Path(tmp)
        video = root / "sample.avi"
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 5, (32, 32))
        assert writer.isOpened()
        for _ in range(6):
            writer.write(np.zeros((32, 32, 3), dtype=np.uint8))
        writer.release()

        class Detector:
            calls = 0

            def detect(self, frame, classes):
                assert classes == ("cat", "dog")
                self.calls += 1
                if self.calls == 2:
                    return []
                return [SimpleNamespace(cls="cat", box=[-1, 1, 25, 25], conf=0.9),
                        SimpleNamespace(cls="cat", box=[0, 1, 25, 25], conf=0.8)]

        args = argparse.Namespace(force=False, sample_stride=5, threshold=0.3, text_threshold=0.3)
        result = prepare.detect_video(video.name, root, root / "assets", Detector(), {}, args)
        assert list(result["anchors"]) == ["0", "5"]
        assert result["anchors"]["0"]["cat_count"] == 1
        assert len(result["anchors"]["0"]["raw_candidates"]) == 2
        assert result["anchors"]["0"]["raw_candidates"][0]["box"][0] == -1
        assert result["anchors"]["5"]["raw_candidates"] == []
        saved = json.loads((root / "assets/detections/sample.json").read_text())
        assert saved["anchors"] == result["anchors"]
        model = root / "model"
        model.mkdir()
        (model / "model.safetensors").write_bytes(b"weight")
        (model / "config.json").write_text("{}")
        args.model_dir = str(model)
        old_fingerprint = prepare.detection_fingerprint_for_args(args)
        args.require_raw_candidates = True
        fingerprint = prepare.detection_fingerprint_for_args(args)
        assert fingerprint == {**old_fingerprint, "raw_candidates_version": 1}
        try:
            saved["fingerprint"] = old_fingerprint
            (root / "assets/detections/sample.json").write_text(json.dumps(saved))
            prepare.load_reusable_detection(root / "assets/detections/sample.json", video, result["source_sha256"], fingerprint)
        except RuntimeError as exc:
            assert "settings mismatch" in str(exc)
        else:
            raise AssertionError("old fingerprint was silently reused")
