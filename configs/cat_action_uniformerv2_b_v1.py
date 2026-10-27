"""UniFormerV2-B (8 frames, 224px) on the seven-class cat action v1."""

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
result_root = "results/training/cat_action_v1/uniformerv2_b"
PRETRAINED = "checkpoints/uniformerv2-base/uniformerv2-base_pretrained.pth"
class_weight = [0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]

model = dict(
    type="Recognizer3D",
    backbone=dict(
        type="UniFormerV2",
        input_resolution=224,
        patch_size=16,
        width=768,
        layers=12,
        heads=12,
        t_size=8,
        dw_reduction=1.5,
        backbone_drop_path_rate=0.0,
        temporal_downsample=False,
        no_lmhra=True,
        double_lmhra=True,
        return_list=[8, 9, 10, 11],
        n_layers=4,
        n_dim=768,
        n_head=12,
        mlp_factor=4.0,
        drop_path_rate=0.0,
        mlp_dropout=[0.5, 0.5, 0.5, 0.5],
        clip_pretrained=False,
        init_cfg=dict(type="Pretrained", checkpoint=PRETRAINED, prefix="backbone."),
    ),
    cls_head=dict(
        type="UniFormerHead",
        dropout_ratio=0.5,
        num_classes=7,
        in_channels=768,
        loss_cls=dict(type="CrossEntropyLoss", class_weight=class_weight),
        average_clips="prob",
    ),
    data_preprocessor=dict(
        type="ActionDataPreprocessor",
        mean=[114.75, 114.75, 114.75],
        std=[57.375, 57.375, 57.375],
        format_shape="NCTHW",
    ),
)

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="UniformSample", clip_len=8, num_clips=1),
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
    dict(type="UniformSample", clip_len=8, num_clips=1, test_mode=True),
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
    clip_grad=dict(max_norm=20, norm_type=2),
    accumulative_counts=2,
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=2),
    dict(type="CosineAnnealingLR", eta_min=1e-6, by_epoch=True, begin=2, end=20),
]
work_dir = f"{result_root}/work"
