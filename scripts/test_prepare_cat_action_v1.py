#!/usr/bin/env python3
"""Minimal tests for the seven-class cat action index generator."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prepare_cat_action_v1 as prep


def row(video: str, task_id: int, start: int, end: int, label: str) -> dict:
    return {
        "video": video,
        "task_id": task_id,
        "start_frame": start,
        "end_frame": end,
        "label": label,
    }


class MappingAndFilteringTests(unittest.TestCase):
    def test_mapping_merges_abnormal_and_keeps_toileting(self) -> None:
        self.assertEqual(prep.map_label("abnormal/scratching"), "abnormal")
        self.assertEqual(prep.map_label("abnormal/gnawing"), "abnormal")
        self.assertEqual(prep.map_label("abnormal/fall"), "abnormal")
        self.assertEqual(prep.map_label("abnormal/seizure"), "abnormal")
        self.assertEqual(prep.map_label("common/toileting"), "toileting")
        self.assertIsNone(prep.map_label("common/multi_cat_chase"))
        self.assertIsNone(prep.map_label("common/multi_cat_roughplay"))

    def test_overlap_short_and_excluded_are_counted(self) -> None:
        rows = [
            row("videos/event_20260101_a.mp4", 1, 1, 100, "common/activity"),
            row("videos/event_20260101_a.mp4", 2, 200, 300, "common/grooming"),
            row("videos/event_20260102_b.mp4", 3, 1, 100, "common/activity"),
            row("videos/event_20260102_b.mp4", 4, 50, 150, "common/eating"),
            row("videos/event_20260103_c.mp4", 5, 1, 100, "common/multi_cat_chase"),
            row("videos/event_20260104_d.mp4", 6, 1, 100, "common/toileting"),
            row("videos/event_20260105_e.mp4", 7, 1, 30, "common/activity"),
        ]
        candidates, filters, excluded, class_counts = prep.build_candidates(rows)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(filters["overlapping"], 2)
        self.assertEqual(filters["excluded_label"], 1)
        self.assertEqual(filters["too_short"], 1)
        self.assertEqual(excluded["common/multi_cat_chase"], 1)
        self.assertEqual(class_counts, {"activity": 1, "grooming": 1, "toileting": 1})
        self.assertEqual(len({c["sample_id"] for c in candidates}), 3)


class SplitTests(unittest.TestCase):
    def test_split_is_day_disjoint_and_deterministic(self) -> None:
        candidates = []
        for day_index in range(10):
            day = f"202601{day_index + 1:02d}"
            for label_index, name in enumerate(prep.CLASSES):
                candidates.append({
                    "day": day,
                    "label": label_index,
                    "label_name": name,
                    "sample_id": f"{day}-{name}",
                })
        groups, seed = prep.find_split(
            candidates, seed_limit=100, train_min=1, eval_min=1,
            toileting_train_min=1, toileting_eval_min=1,
        )
        self.assertEqual(seed, 0)
        self.assertFalse(groups["train"] & groups["val"])
        self.assertFalse(groups["train"] & groups["test"])
        self.assertFalse(groups["val"] & groups["test"])
        self.assertEqual(set().union(*groups.values()), {f"202601{i + 1:02d}" for i in range(10)})
        groups_again, seed_again = prep.find_split(
            candidates, seed_limit=100, train_min=1, eval_min=1,
            toileting_train_min=1, toileting_eval_min=1,
        )
        self.assertEqual((groups, seed), (groups_again, seed_again))


class OutputTests(unittest.TestCase):
    def test_outputs_are_reproducible_and_source_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "datasets/cat_raw/annotations/intervals.csv"
            source.parent.mkdir(parents=True)
            source.write_text("video,task_id,start_frame,end_frame,label\n", encoding="utf-8")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            candidates = [
                {
                    "video": "videos/event_20260101_a.mp4",
                    "task_id": 1,
                    "start_frame": 1,
                    "end_frame": 100,
                    "label": 0,
                    "label_name": "activity",
                    "source_label": "common/activity",
                    "day": "20260101",
                    "sample_id": "sample-train",
                },
                {
                    "video": "videos/event_20260102_b.mp4",
                    "task_id": 2,
                    "start_frame": 1,
                    "end_frame": 100,
                    "label": 5,
                    "label_name": "toileting",
                    "source_label": "common/toileting",
                    "day": "20260102",
                    "sample_id": "sample-val",
                },
            ]
            groups = {"train": {"20260101"}, "val": {"20260102"}, "test": set()}
            kwargs = dict(
                root=root,
                source=source,
                candidates=candidates,
                split_groups=groups,
                split_seed=11,
                filter_counts=Counter(),
                excluded_counts=Counter(),
                class_counts={"activity": 1, "toileting": 1},
                video_check={"enabled": False},
                force=False,
            )
            first = prep.write_outputs(**kwargs)
            out_dir = root / "datasets/cat_action_v1"
            first_hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in out_dir.iterdir()
            }
            second = prep.write_outputs(**kwargs)
            second_hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in out_dir.iterdir()
            }
            self.assertEqual(first_hashes, second_hashes)
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)
            manifest = json.loads((out_dir / "split_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["seed"], 11)
            self.assertEqual(manifest["classes"], prep.CLASSES)
            self.assertTrue((out_dir / "val_balanced.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
