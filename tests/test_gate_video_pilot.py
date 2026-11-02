import csv
import argparse
import json
import shutil
import uuid
from pathlib import Path

import pytest

from scripts.train_gate_video import (
    build_eval_binding,
    choose_threshold,
    claim_finalization,
    load_rows,
    metrics_at,
    validate_eval_binding,
)


def write_review(root: Path, *, cross_split_source: bool = False) -> None:
    items = [
        {"path": "a.mp4", "file": "a.mp4", "source_id": "a", "video": "source-a.mp4",
         "split": "train", "domain": "day", "label_scope": "any_pet_in_window"},
        {"path": "b.mp4", "file": "b.mp4", "source_id": "a" if cross_split_source else "b",
         "video": "source-a.mp4" if cross_split_source else "source-b.mp4",
         "split": "val", "domain": "night", "label_scope": "any_pet_in_window"},
    ]
    (root / "items.json").write_text(json.dumps({"mode": "video", "items": items}), encoding="utf-8")
    (root / "a.mp4").write_bytes(b"a")
    (root / "b.mp4").write_bytes(b"b")
    with (root / "labels.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "human_label"])
        writer.writeheader()
        writer.writerow({"path": "a.mp4", "human_label": "present"})
        writer.writerow({"path": "b.mp4", "human_label": "absent"})


@pytest.fixture
def review_root() -> Path:
    """Use the repository-mandated results/tests location for test fixtures."""
    root = Path(__file__).resolve().parents[1] / "results" / "tests" / f"gate-video-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root)


def test_load_rows_validates_complete_labels(review_root: Path) -> None:
    write_review(review_root)
    rows = load_rows(review_root, review_root / "labels.csv")
    assert [row["label"] for row in rows] == [1, 0]
    assert rows[0]["label_scope"] == "any_pet_in_window"


def test_load_rows_rejects_unresolved_label(review_root: Path) -> None:
    write_review(review_root)
    with (review_root / "labels.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "human_label"])
        writer.writeheader()
        writer.writerow({"path": "a.mp4", "human_label": "uncertain"})
        writer.writerow({"path": "b.mp4", "human_label": "absent"})
    with pytest.raises(ValueError, match="unresolved label"):
        load_rows(review_root, review_root / "labels.csv")


def test_load_rows_rejects_source_leakage(review_root: Path) -> None:
    write_review(review_root, cross_split_source=True)
    with pytest.raises(ValueError, match="source occurs in multiple splits"):
        load_rows(review_root, review_root / "labels.csv")


def test_load_rows_rejects_unapproved_label_scope(review_root: Path) -> None:
    write_review(review_root)
    data = json.loads((review_root / "items.json").read_text(encoding="utf-8"))
    data["items"][0]["label_scope"] = "last_frame"
    (review_root / "items.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported label_scope"):
        load_rows(review_root, review_root / "labels.csv")


def test_metrics_and_threshold() -> None:
    probabilities = [0.9, 0.8, 0.2, 0.1]
    targets = [1, 1, 0, 0]
    assert metrics_at(probabilities, targets, 0.5)["tp"] == 2
    assert choose_threshold(probabilities, targets, target_miss=0.0) == pytest.approx(0.8)


def test_eval_binding_rejects_changed_input(review_root: Path) -> None:
    pretrained = review_root / "pretrained.pth"
    best = review_root / "best.pt"
    threshold = review_root / "threshold.json"
    labels = review_root / "labels.csv"
    items = review_root / "items.json"
    for path, content in ((pretrained, "pretrain"), (best, "best"), (threshold, "threshold"),
                          (labels, "labels"), (items, "items")):
        path.write_text(content, encoding="utf-8")
    args = argparse.Namespace(review_root=review_root, labels=labels, checkpoint=pretrained,
                              frames=4, height=160, width=288, seed=0, batch=8)
    binding = build_eval_binding(args, best, threshold)
    validate_eval_binding({"eval_binding": binding}, args, best, threshold)
    changed = argparse.Namespace(**{**vars(args), "frames": 8})
    with pytest.raises(ValueError, match="frames"):
        validate_eval_binding({"eval_binding": binding}, changed, best, threshold)


def test_claim_finalization_is_atomic(review_root: Path) -> None:
    claim_finalization(review_root)
    assert (review_root / "finalization.lock").is_file()
    with pytest.raises(FileExistsError, match="another finalization process"):
        claim_finalization(review_root)
