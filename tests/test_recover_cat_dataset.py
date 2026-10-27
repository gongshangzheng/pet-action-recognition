#!/usr/bin/env python3
"""Safety checks for streaming recovery; fixtures stay inside project results/."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import unittest
import uuid

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from recover_cat_dataset import ROOT, inspect_archive


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = ROOT / "results" / "tests" / f"cat_recovery_test_{uuid.uuid4().hex}"
        self.scratch.mkdir(parents=True, exist_ok=False)
        self.assertIn(ROOT.resolve(), self.scratch.resolve().parents)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        target = self.scratch.resolve()
        if ROOT.resolve() not in target.parents or target.name.startswith("cat_recovery_test_") is False:
            raise RuntimeError("Refusing to delete an unexpected test path")
        shutil.rmtree(target)

    def archive(self, records):
        handle = io.BytesIO()
        with tarfile.open(fileobj=handle, mode="w") as archive:
            for name, payload in records:
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        blob = handle.getvalue()
        cuts = (733, 7777)
        parts = []
        for index, fragment in enumerate((blob[:cuts[0]], blob[cuts[0]:cuts[1]], blob[cuts[1]:])):
            part = self.scratch / f"cat_raw.tar.part-{index:03d}"
            part.write_bytes(fragment)
            parts.append(part)
        return parts

    def test_stream_crosses_part_boundaries_and_verifies_content(self):
        payload = b"a" * 9031
        name = "dataset-wyy/event_example.mp4"
        parts = self.archive([(name, payload)])
        expected = {name: (len(payload), hashlib.sha256(payload).hexdigest())}
        records, hashes = inspect_archive(parts, expected)
        self.assertEqual(records[0]["source"], name)
        self.assertEqual(set(hashes), {part.name for part in parts})
        output = self.scratch / "output"
        output.mkdir()
        inspect_archive(parts, expected, output)
        self.assertEqual((output / "videos" / "event_example.mp4").read_bytes(), payload)

    def test_rejects_traversal_without_writing(self):
        payload = b"bad"
        name = "dataset-wyy/../outside.mp4"
        parts = self.archive([(name, payload)])
        expected = {name: (len(payload), hashlib.sha256(payload).hexdigest())}
        output = self.scratch / "output"
        output.mkdir()
        with self.assertRaisesRegex(ValueError, "Windows-unsafe"):
            inspect_archive(parts, expected, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_rejects_corrupt_payload_and_duplicate_member(self):
        name = "annotation-wyy/merged_annotations.csv"
        parts = self.archive([(name, b"wrong")])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            inspect_archive(parts, {name: (5, hashlib.sha256(b"right").hexdigest())})
        parts = self.archive([(name, b"right"), (name, b"right")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inspect_archive(parts, {name: (5, hashlib.sha256(b"right").hexdigest())})


if __name__ == "__main__":
    unittest.main()
