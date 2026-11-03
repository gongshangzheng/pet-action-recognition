"""VideoMAEv2-B GroundingDINO-crop arm for the paired cat crop experiment."""

_base_ = [
    "./cat_crop_videomaev2_raw.py",
]

classes = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]
result_root = "results/cat_crop_classification/gdino-crop-20261103a/gdino"
data_root = (
    "results/cat_crop_classification/gdino-crop-20261103a/"
    "assets/gdino-v1"
)

train_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/gdino_train.jsonl",
        data_prefix=dict(video=data_root),
    )
)
val_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/gdino_val.jsonl",
        data_prefix=dict(video=data_root),
    )
)
test_dataloader = dict(
    dataset=dict(
        ann_file=f"{index_root}/gdino_test.jsonl",
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
