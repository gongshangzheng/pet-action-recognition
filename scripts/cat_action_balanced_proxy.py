#!/usr/bin/env python3
"""Interval-level miss-rate proxy from saved test predictions.

Two views, both recomputed from ``test_metrics.json`` without new inference:

- natural test split: micro error over every test interval;
- balanced diagnostic split: error over the fixed balanced subset, which is a
  macro-like proxy because every class contributes the same number of rows.

Neither is an event-level miss rate on continuous video.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def balanced_ids(index_root: Path) -> list[str]:
    path = index_root / "test_balanced.jsonl"
    return [json.loads(line)["sample_id"] for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prediction_error(metrics: dict, sample_ids: list[str] | None) -> dict:
    rows = metrics["predictions"]
    if sample_ids is not None:
        wanted = set(sample_ids)
        rows = [row for row in rows if row["sample_id"] in wanted]
        missing = len(wanted) - len(rows)
        if missing:
            raise AssertionError(f"{missing} balanced samples missing from predictions")
    wrong = sum(row["predicted"] != row["label"] for row in rows)
    return {"samples": len(rows), "wrong": wrong,
            "error_percent": 100.0 * wrong / len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=str(ROOT / "results/training/cat_action_v1"))
    parser.add_argument("--index", default=str(ROOT / "datasets/cat_action_v1"))
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args()
    ids = balanced_ids(Path(args.index))
    for name in args.models:
        metrics = json.loads((Path(args.results) / name / "test_metrics.json")
                             .read_text(encoding="utf-8"))
        natural = prediction_error(metrics, None)
        balanced = prediction_error(metrics, ids)
        print(json.dumps({"model": name, "natural": natural, "balanced": balanced,
                          "balanced_support": len(ids)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
