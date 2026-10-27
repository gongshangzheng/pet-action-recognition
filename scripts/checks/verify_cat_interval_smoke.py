#!/usr/bin/env python3
"""Verify the lab smoke run produced a complete, internally consistent record."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/training/cat_interval_smoke"
INDEX = ROOT / "datasets/cat_interval_smoke"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    state = read(RESULT / "run_status.json")
    assert state["status"] == "complete" and state["train_exit_code"] == 0
    assert state["test_exit_code"] == 0
    assert state["purpose"] == "pipeline smoke test only"
    assert sha256(Path(state["config"])) == state["config_sha256"]
    checkpoint = Path(state["checkpoint"])
    assert checkpoint.is_file() and checkpoint.stat().st_size > 0

    audit = read(RESULT / "data_audit.json")
    assert audit["purpose"] == "pipeline smoke test only"
    classes = read(INDEX / "classes.json")
    split_days = {}
    split_rows = {}
    for split, count in (("train", 12), ("val", 6), ("test", 6)):
        path = INDEX / f"{split}.jsonl"
        assert sha256(path) == state["dataset_sha256"][split]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == count
        assert Counter(row["label"] for row in rows) == Counter(
            {label: 2 if split == "train" else 1 for label in range(len(classes))})
        split_rows[split] = rows
        split_days[split] = {re.search(r"event_(20\d{6})_", row["video"]).group(1)
                             for row in rows}
    assert not (split_days["train"] & split_days["val"])
    assert not (split_days["train"] & split_days["test"])
    assert not (split_days["val"] & split_days["test"])

    metrics = {}
    for split in ("val", "test"):
        report = read(RESULT / f"{split}_metrics.json")
        rows = split_rows[split]
        assert report["samples"] == len(rows)
        assert report["classes"] == classes
        assert len(report["per_class"]) == len(classes)
        matrix = report["confusion_matrix"]
        assert len(matrix) == len(classes) and all(len(row) == len(classes) for row in matrix)
        assert sum(map(sum, matrix)) == len(rows)
        predictions = report["predictions"]
        assert len(predictions) == len(rows)
        assert {row["sample_id"] for row in predictions} == {row["sample_id"] for row in rows}
        for row in predictions:
            assert row["video"] and row["start_frame"] and row["end_frame"]
            assert len(row["scores"]) == len(classes)
            assert all(math.isfinite(score) for score in row["scores"])
        metrics[split] = {key: report[key] for key in
                          ("samples", "top1_acc_percent", "macro_f1_percent",
                           "balanced_acc_percent")}

    assert (RESULT / "preflight.json").is_file()
    assert (RESULT / "train.log").stat().st_size > 0
    assert (RESULT / "test.log").stat().st_size > 0
    report = {"status": "verified", "purpose": "pipeline smoke test only",
              "train_samples": len(split_rows["train"]), "checkpoint_bytes": checkpoint.stat().st_size,
              "metrics": metrics, "files": [str(RESULT / name) for name in
                                         ("run_status.json", "data_audit.json", "preflight.json",
                                          "train.log", "test.log", "val_metrics.json",
                                          "test_metrics.json")],
              "checkpoint": str(checkpoint)}
    (RESULT / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
