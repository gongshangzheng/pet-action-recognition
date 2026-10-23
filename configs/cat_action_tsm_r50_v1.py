"""Seven-class interval-aware TSM R50 baseline for cat action v1."""

_base_ = [
    "../models/mmaction2/configs/recognition/tsm/"
    "tsm_imagenet-pretrained-r50_8xb16-1x1x8-50e_kinetics400-rgb.py"
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
# Inverse-square-root weights from the verified v1 training split:
# activity 998, eating 200, drinking 93, stationary 216, grooming 48,
# toileting 20, abnormal 89.
class_weight = [0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]

data_root = "datasets/cat_raw"
index_root = "datasets/cat_action_v1"
result_root = "results/training/cat_action_v1/tsm_r50"

custom_imports = dict(
    imports=["petlib.datasets.cat_intervals"], allow_failed_imports=False
)

model = dict(
    backbone=dict(
        pretrained=None,
        pretrained2d=False,
        init_cfg=dict(
            type="Pretrained",
            checkpoint="checkpoints/tsm-resnet50/tsm-resnet50_pretrained.pth",
            prefix="backbone.",
        ),
    ),
    cls_head=dict(
        num_classes=len(classes),
        loss_cls=dict(type="CrossEntropyLoss", class_weight=class_weight),
    ),
)

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=8),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(
        type="MultiScaleCrop",
        input_size=224,
        scales=(1, 0.875, 0.75, 0.66),
        random_crop=False,
        max_wh_scale_gap=1,
        num_fixed_crops=13,
    ),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="ColorJitter", brightness=0.2, contrast=0.2,
         saturation=0.0, hue=0.0),
    dict(type="FormatShape", input_format="NCHW"),
    dict(
        type="PackActionInputs",
        meta_keys=("filename", "interval_start", "interval_end", "sample_id"),
    ),
]
eval_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(
        type="SampleFrames",
        clip_len=1,
        frame_interval=1,
        num_clips=8,
        test_mode=True,
    ),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCHW"),
    dict(
        type="PackActionInputs",
        meta_keys=("filename", "interval_start", "interval_end", "sample_id"),
    ),
]

train_dataloader = dict(
    batch_size=16,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=True),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/train.jsonl",
        data_prefix=dict(video=data_root),
        pipeline=train_pipeline,
    ),
)
val_dataloader = dict(
    batch_size=16,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/val.jsonl",
        data_prefix=dict(video=data_root),
        pipeline=eval_pipeline,
        test_mode=True,
    ),
)
test_dataloader = dict(
    batch_size=16,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type="IntervalVideoDataset",
        ann_file=f"{index_root}/test.jsonl",
        data_prefix=dict(video=data_root),
        pipeline=eval_pipeline,
        test_mode=True,
    ),
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

optim_wrapper = dict(
    constructor="TSMOptimWrapperConstructor",
    paramwise_cfg=dict(fc_lr5=True),
    optimizer=dict(type="SGD", lr=0.005, momentum=0.9, weight_decay=0.0001),
    clip_grad=dict(max_norm=20, norm_type=2),
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=2),
    dict(
        type="CosineAnnealingLR",
        eta_min=0.0,
        by_epoch=True,
        begin=2,
        end=20,
    ),
]
train_cfg = dict(
    type="EpochBasedTrainLoop", max_epochs=20, val_begin=1, val_interval=1
)
val_cfg = dict(type="ValLoop")
test_cfg = dict(type="TestLoop")
default_hooks = dict(
    logger=dict(interval=10),
    checkpoint=dict(
        interval=1, max_keep_ckpts=2, save_best="macro_f1", rule="greater"
    ),
)
randomness = dict(seed=0, deterministic=False)
auto_scale_lr = dict(enable=False, base_batch_size=16)
work_dir = f"{result_root}/work"
