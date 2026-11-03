"""VideoMAEv2-B raw-video arm for the paired cat crop experiment."""

_base_ = [
    "./cat_action_videomaev2_b_v1.py",
]

run_id = "gdino-crop-20261103a"
result_root = f"results/cat_crop_classification/{run_id}/raw"
data_root = "datasets/cat_raw"
index_root = "datasets/cat_crop_classification/gdino-v1"

train_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/raw_train.jsonl",
        data_prefix=dict(video=data_root),
    )
)
val_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/raw_val.jsonl",
        data_prefix=dict(video=data_root),
    )
)
test_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/raw_test.jsonl",
        data_prefix=dict(video=data_root),
    )
)
val_evaluator = dict(
    type="CatIntervalMetric",
    classes=classes,
    out_file=f"{result_root}/val_metrics.json",
)
test_evaluator = dict(
    type="CatIntervalMetric",
    classes=classes,
    out_file=f"{result_root}/test_metrics.json",
)
work_dir = f"{result_root}/work"
