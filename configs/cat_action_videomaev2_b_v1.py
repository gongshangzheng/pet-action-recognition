"""VideoMAEv2-B (16 frames x stride 4, 224px) on the seven-class cat action v1."""

_base_ = [
    "./cat_action_v1_base.py",
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
result_root = "results/training/cat_action_v1/videomaev2_b"
PRETRAINED = "checkpoints/videomaev2-base/videomaev2-base_pretrained.pth"
class_weight = [0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]

model = dict(
    type="Recognizer3D",
    backbone=dict(
        type="VisionTransformer",
        img_size=224,
        patch_size=16,
        embed_dims=768,
        depth=12,
        num_heads=12,
        mlp_ratio=4,
        qkv_bias=True,
        num_frames=16,
        drop_path_rate=0.1,
        norm_cfg=dict(type="LN", eps=1e-6),
        init_cfg=dict(type="Pretrained", checkpoint=PRETRAINED, prefix="backbone."),
    ),
    cls_head=dict(
        type="TimeSformerHead",
        num_classes=7,
        in_channels=768,
        dropout_ratio=0.0,
        loss_cls=dict(type="CrossEntropyLoss", class_weight=class_weight),
        average_clips="prob",
    ),
    data_preprocessor=dict(
        type="ActionDataPreprocessor",
        mean=[123.675, 116.28, 103.53],
        std=[58.395, 57.12, 57.375],
        format_shape="NCTHW",
    ),
)

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=16, frame_interval=4, num_clips=1),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="RandomResizedCrop", area_range=(0.5, 1.0)),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]
eval_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=16, frame_interval=4, num_clips=1, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]

train_dataloader = dict(batch_size=8, dataset=dict(pipeline=train_pipeline))
val_dataloader = dict(batch_size=8, dataset=dict(pipeline=eval_pipeline))
test_dataloader = dict(batch_size=8, dataset=dict(pipeline=eval_pipeline))

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
    optimizer=dict(type="AdamW", lr=5e-5, betas=(0.9, 0.999), weight_decay=0.05),
    paramwise_cfg=dict(norm_decay_mult=0.0, bias_decay_mult=0.0),
    clip_grad=dict(max_norm=1.0),
    accumulative_counts=2,
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=2),
    dict(type="CosineAnnealingLR", eta_min=1e-6, by_epoch=True, begin=2, end=20),
]
work_dir = f"{result_root}/work"
