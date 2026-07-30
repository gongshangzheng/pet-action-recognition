# 哺乳动物动作识别 VideoMAEv2 配置（ViT-B, 16 frames, 224px）
# 适配 pet_action_mammal_v0（640x360, 24fps, 7 训练类 + 1 保留类）
#
# Finetune：backbone 从 K710 蒸馏预训练 ckpt 加载（init_cfg=Pretrained），
# cls_head 7 类随机初始化（K400 ckpt 的 400 类 head 形状不匹配，丢弃）。
# 不用 train_model.py --pretrained（那会注入 load_from 整模加载，触发 head 形状不匹配）。
_base_ = ["../models/mmaction2/configs/_base_/default_runtime.py"]

PRETRAINED = "checkpoints/videomaev2-base/videomaev2-base_pretrained.pth"
num_classes = 7

# model settings（与 mmaction2 videomaev2 base 一致，仅 cls_head 改 7 类 + backbone init_cfg）
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
        norm_cfg=dict(type="LN", eps=1e-6),
        init_cfg=dict(type="Pretrained", checkpoint=PRETRAINED, prefix="backbone."),
    ),
    cls_head=dict(
        type="TimeSformerHead",
        num_classes=num_classes,
        in_channels=768,
        average_clips="prob",
    ),
    data_preprocessor=dict(
        type="ActionDataPreprocessor",
        mean=[123.675, 116.28, 103.53],
        std=[58.395, 57.12, 57.375],
        format_shape="NCTHW",
    ),
)

# dataset settings
dataset_type = "VideoDataset"
data_root = "datasets/pet_action_mammal_v0"
data_root_val = "datasets/pet_action_mammal_v0"
ann_file_train = "datasets/pet_action_mammal_v0/annotation/train_public.txt"
ann_file_val = "datasets/pet_action_mammal_v0/annotation/val_public.txt"
ann_file_test = "datasets/pet_action_mammal_v0/annotation/test_public.txt"

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=16, frame_interval=4, num_clips=1),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 224)),
    dict(type="RandomResizedCrop", area_range=(0.5, 1.0)),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs"),
]
val_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=16, frame_interval=4, num_clips=1, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 224)),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs"),
]
test_pipeline = val_pipeline

train_dataloader = dict(
    batch_size=2,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=True),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_train,
        data_prefix=dict(video=data_root),
        pipeline=train_pipeline,
    ),
)
val_dataloader = dict(
    batch_size=2,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_val,
        data_prefix=dict(video=data_root_val),
        pipeline=val_pipeline,
        test_mode=True,
    ),
)
test_dataloader = dict(
    batch_size=1,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_test,
        data_prefix=dict(video=data_root_val),
        pipeline=test_pipeline,
        test_mode=True,
    ),
)

val_evaluator = dict(type="AccMetric")
test_evaluator = val_evaluator
test_cfg = dict(type="TestLoop")

# VideoMAE finetune：AdamW + warmup + cosine
optim_wrapper = dict(
    optimizer=dict(type="AdamW", lr=1e-4, weight_decay=0.05),
    clip_grad=dict(max_norm=1.0),
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=5),
    dict(type="CosineAnnealingLR", T_max=25, eta_min=1e-6, by_epoch=True, begin=5, end=30),
]
train_cfg = dict(type="EpochBasedTrainLoop", max_epochs=30, val_begin=1, val_interval=1)
val_cfg = dict(type="ValLoop")

default_hooks = dict(checkpoint=dict(interval=5, max_keep_ckpts=3, save_best="auto"))
auto_scale_lr = dict(enable=False, base_batch_size=256)

# 训练中定期可视化（每 5 epoch）
custom_imports = dict(imports=["configs.hooks.vis_samples_hook"], allow_failed_imports=True)
custom_hooks = [
    dict(
        type="VisSamplesHook",
        interval=5,
        num_samples=6,
        ann_file="",
        data_root="",
        dataset_root="",
    )
]
