"""Shared data and loop settings for the cat action v1 reference models.

Children define the model, pipelines, batch size, optimizer, schedule, the
evaluators' output files and ``work_dir``. Same seven-class index and split as
the TSN/TSM baselines.
"""

_base_ = ["../models/mmaction2/configs/_base_/default_runtime.py"]

classes = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]
# Inverse-square-root weights from the verified v1 training split.
class_weight = [0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]

data_root = "datasets/cat_raw"
index_root = "datasets/cat_action_v1"

custom_imports = dict(
    imports=["petlib.datasets.cat_intervals"], allow_failed_imports=False
)

train_dataloader = dict(
    num_workers=8,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=True),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/train.jsonl",
        data_prefix=dict(video=data_root),
    ),
)
val_dataloader = dict(
    num_workers=8,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/val.jsonl",
        data_prefix=dict(video=data_root),
        test_mode=True,
    ),
)
test_dataloader = dict(
    num_workers=8,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/test.jsonl",
        data_prefix=dict(video=data_root),
        test_mode=True,
    ),
)

train_cfg = dict(
    type="EpochBasedTrainLoop", max_epochs=20, val_begin=1, val_interval=1
)
val_cfg = dict(type="ValLoop")
test_cfg = dict(type="TestLoop")
default_hooks = dict(
    logger=dict(interval=10),
    checkpoint=dict(
        interval=1,
        max_keep_ckpts=2,
        save_best="macro_f1",
        rule="greater",
        save_optimizer=False,
        save_param_scheduler=False,
    ),
)
randomness = dict(seed=0, deterministic=False)
auto_scale_lr = dict(enable=False, base_batch_size=16)
