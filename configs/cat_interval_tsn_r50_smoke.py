"""Minimal workflow check; its metrics are not estimates of model quality."""

_base_ = ["./cat_interval_tsn_r50_baseline.py"]

train_dataloader = dict(
    batch_size=2, num_workers=0, persistent_workers=False,
    dataset=dict(ann_file="datasets/cat_interval_smoke/train.jsonl"))
val_dataloader = dict(
    batch_size=2, num_workers=0, persistent_workers=False,
    dataset=dict(ann_file="datasets/cat_interval_smoke/val.jsonl"))
test_dataloader = dict(
    batch_size=2, num_workers=0, persistent_workers=False,
    dataset=dict(ann_file="datasets/cat_interval_smoke/test.jsonl"))

train_cfg = dict(max_epochs=1)
val_evaluator = dict(out_file="results/training/cat_interval_smoke/val_metrics.json")
test_evaluator = dict(out_file="results/training/cat_interval_smoke/test_metrics.json")
work_dir = "results/training/cat_interval_smoke/work"
