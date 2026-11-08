"""Source-failure ledger validation for the guarded base extraction runner."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gdino_base_raw", ROOT / "scripts/remote/run_gdino_base_raw.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class SourceFailuresTest(unittest.TestCase):
    def test_validate_explicit_source_and_reject_changes(self):
        parent = ROOT / "results/tests"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root = Path(directory)
            (root / "videos").mkdir()
            source = root / "videos/bad.mp4"
            source.write_bytes(b"broken")
            manifest = root / "videos.txt"
            manifest.write_text("videos/bad.mp4\nvideos/good.mp4\n")
            ledger = root / "failures.json"
            entry = {"video": "videos/bad.mp4", "status": "source_unreadable", "size_bytes": 6,
                     "source_sha256": hashlib.sha256(b"broken").hexdigest(), "error": "cannot open"}
            data = {"schema": "gdino-source-failures-v1", "manifest_sha256": runner.digest(manifest),
                    "checked": 2, "failures": [entry]}
            ledger.write_text(json.dumps(data))
            videos = manifest.read_text().splitlines()
            self.assertEqual(runner.load_source_failures(ledger, manifest, videos, root), {"videos/bad.mp4"})
            source.write_bytes(b"change")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                runner.load_source_failures(ledger, manifest, videos, root)
            source.write_bytes(b"broken")
            data["failures"].append(entry)
            ledger.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "invalid source failure entry"):
                runner.load_source_failures(ledger, manifest, videos, root)
            data["failures"] = [entry]
            data["manifest_sha256"] = "wrong"
            ledger.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "invalid source failure ledger"):
                runner.load_source_failures(ledger, manifest, videos, root)


if __name__ == "__main__":
    unittest.main()
