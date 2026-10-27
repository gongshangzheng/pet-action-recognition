"""Check non-destructive, repeatable weight linking using tiny synthetic files."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.migration.link_cat_action_checkpoints import apply_links, plan_links


class CheckpointLinkTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / "results/tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.root / "configs").mkdir()
        (self.root / "configs/model.py").write_text("# fixture\n")
        self.target = self.source / "best.pth"
        self.target.write_bytes(b"synthetic checkpoint")
        self.records = [{"model": "model", "config": "configs/model.py",
                         "checkpoint": "best.pth",
                         "sha256": hashlib.sha256(self.target.read_bytes()).hexdigest()}]

    def test_dry_run_link_and_repeat_preserve_source(self):
        before = self.target.stat()
        planned = plan_links(self.root, self.source, self.records)
        link = Path(planned[0]["link"])
        self.assertFalse(link.parent.exists())
        apply_links(planned)
        self.assertEqual(link.resolve(), self.target)
        repeated = plan_links(self.root, self.source, self.records)
        self.assertEqual(repeated[0]["state"], "existing")
        apply_links(repeated)
        self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.target.read_bytes(), b"synthetic checkpoint")

    def test_existing_file_is_not_replaced(self):
        link = self.root / "checkpoints/cat_action_v1/model/best.pth"
        link.parent.mkdir(parents=True)
        link.write_bytes(b"keep me")
        with self.assertRaises(FileExistsError):
            plan_links(self.root, self.source, self.records)
        self.assertEqual(link.read_bytes(), b"keep me")

    def test_bad_hash_or_escaped_source_creates_nothing(self):
        bad = [{**self.records[0], "sha256": "0" * 64}]
        with self.assertRaises(ValueError):
            plan_links(self.root, self.source, bad)
        escaped = [{**self.records[0], "checkpoint": "../best.pth"}]
        with self.assertRaises(ValueError):
            plan_links(self.root, self.source, escaped)
        self.assertFalse((self.root / "checkpoints").exists())

    def test_directory_symlink_is_rejected(self):
        (self.root / "checkpoints").symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            plan_links(self.root, self.source, self.records)


if __name__ == "__main__":
    unittest.main()
