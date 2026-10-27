"""X3D-S (13 frames x stride 3, 182px) on the seven-class cat action v1.

The X3D backbone ignores ``init_cfg``; weights are loaded via ``load_from``
(head shape mismatches are skipped by the runner). Source video is 15 fps, so
stride 3 covers the same time span as K400's stride 6 at 30 fps.
"""

_base_ = [
    "./cat_action_v1_base.py",
    "../models/mmaction2/configs/_base_/models/x3d.py",
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
result_root = "results/training/cat_action_v1/x3d_s"
class_weight = [0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]
load_from = "checkpoints/x3d-xs/x3d-xs_pretrained.pth"

model = dict(
    cls_head=dict(
        num_classes=7,
        loss_cls=dict(type="CrossEntropyLoss", class_weight=class_weight),
    ),
)

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=13, frame_interval=3, num_clips=1),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 182)),
    dict(type="RandomResizedCrop", area_range=(0.5, 1.0)),
    dict(type="Resize", scale=(182, 182), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]
eval_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=13, frame_interval=3, num_clips=1, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 182)),
    dict(type="CenterCrop", crop_size=182),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]

train_dataloader = dict(batch_size=16, dataset=dict(pipeline=train_pipeline))
val_dataloader = dict(batch_size=16, dataset=dict(pipeline=eval_pipeline))
test_dataloader = dict(batch_size=16, dataset=dict(pipeline=eval_pipeline))

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

optim_wrapper = dict(
    type="AmpOptimWrapper",
    optimizer=dict(type="SGD", lr=0.01, momentum=0.9, weight_decay=1e-4),
    clip_grad=dict(max_norm=40, norm_type=2),
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=2),
    dict(type="CosineAnnealingLR", eta_min=0.0, by_epoch=True, begin=2, end=20),
]
work_dir = f"{result_root}/work"
