# 哺乳动物动作识别 UniFormerV2 配置（ViT-B/16, 8 frames, 224px）
# 适配 pet_action_mammal_v0（7 训练类）。
#
# 「图像基础模型适配视频」路线在 mmaction2 的现成代表（CLIP ViT + 时空块）。
# backbone 从 K710 预训练整模 ckpt 加载（prefix=backbone.）；cls_head 7 类随机
# 初始化（vendor K400 config 的 channel_map 是 K710→K400 评测映射，7 类微调用不到）。
#
# 管线差异：vendor 用 PytorchVideoWrapper(RandAugment)，为避免远端额外依赖
# pytorchvideo，这里换成常规 RandomResizedCrop/Flip 组合。
_base_ = ["../models/mmaction2/configs/_base_/default_runtime.py"]

PRETRAINED = "checkpoints/uniformerv2-base/uniformerv2-base_pretrained.pth"
num_classes = 7
num_frames = 8

model = dict(
    type="Recognizer3D",
    backbone=dict(
        type="UniFormerV2",
        input_resolution=224,
        patch_size=16,
        width=768,
        layers=12,
        heads=12,
        t_size=num_frames,
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
        num_classes=num_classes,
        in_channels=768,
        average_clips="prob",
    ),
    data_preprocessor=dict(
        type="ActionDataPreprocessor",
        mean=[114.75, 114.75, 114.75],
        std=[57.375, 57.375, 57.375],
        format_shape="NCTHW",
    ),
)

dataset_type = "VideoDataset"
data_root = "datasets/pet_action_mammal_v0"
data_root_val = "datasets/pet_action_mammal_v0"
ann_file_train = "datasets/pet_action_mammal_v0/annotation/train_public.txt"
ann_file_val = "datasets/pet_action_mammal_v0/annotation/val_public.txt"
ann_file_test = "datasets/pet_action_mammal_v0/annotation/test_public.txt"

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="UniformSample", clip_len=num_frames, num_clips=1),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="RandomResizedCrop"),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs"),
]
val_pipeline = [
    dict(type="DecordInit"),
    dict(type="UniformSample", clip_len=num_frames, num_clips=1, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 224)),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs"),
]
test_pipeline = [
    dict(type="DecordInit"),
    dict(type="UniformSample", clip_len=num_frames, num_clips=4, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 224)),
    dict(type="ThreeCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs"),
]

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

# 全量微调 lr 谨慎（vendor K400 finetune 用 2e-6/5ep）；小数据取 5e-5 折中
optim_wrapper = dict(
    optimizer=dict(type="AdamW", lr=5e-5, betas=(0.9, 0.999), weight_decay=0.05),
    paramwise_cfg=dict(norm_decay_mult=0.0, bias_decay_mult=0.0),
    clip_grad=dict(max_norm=20, norm_type=2),
)
param_scheduler = [
    dict(type="LinearLR", start_factor=0.1, by_epoch=True, begin=0, end=2),
    dict(type="CosineAnnealingLR", T_max=18, eta_min=1e-6, by_epoch=True, begin=2, end=20),
]
train_cfg = dict(type="EpochBasedTrainLoop", max_epochs=20, val_begin=1, val_interval=1)
val_cfg = dict(type="ValLoop")

default_hooks = dict(
    checkpoint=dict(
        interval=5,
        max_keep_ckpts=1,
        save_best="auto",
        save_optimizer=False,
        save_param_scheduler=False,
    )
)
auto_scale_lr = dict(enable=False, base_batch_size=256)
