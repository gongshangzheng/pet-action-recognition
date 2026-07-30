# 哺乳动物动作识别 TSN 配置（标准 256px 分辨率）
# 适配 pet_action_mammal_v0（640x360 真实视频，7 训练类 + 1 保留类）
_base_ = [
    "../models/mmaction2/configs/_base_/models/tsn_r50.py",
    "../models/mmaction2/configs/_base_/schedules/sgd_100e.py",
    "../models/mmaction2/configs/_base_/default_runtime.py",
]

# 占位，实际由 scripts/train_model.py 通过 --cfg-options 覆盖
dataset_type = "VideoDataset"
data_root = "datasets/pet_action_mammal_v0"
data_root_val = "datasets/pet_action_mammal_v0"
data_root_test = "datasets/pet_action_mammal_v0"
ann_file_train = "datasets/pet_action_mammal_v0/annotation/train_public.txt"
ann_file_val = "datasets/pet_action_mammal_v0/annotation/val_public.txt"
ann_file_test = "datasets/pet_action_mammal_v0/annotation/test_public.txt"
num_classes = 8

# 标准 256px pipeline（mmaction2 官方 TSN 标准分辨率）
train_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="RandomResizedCrop", area_range=(0.5, 1.0)),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="Resize", scale=(256, 256), keep_ratio=False),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs"),
]
val_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="CenterCrop", crop_size=256),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs"),
]
test_pipeline = val_pipeline

train_dataloader = dict(
    batch_size=8,
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
    batch_size=8,
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
    batch_size=8,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_test,
        data_prefix=dict(video=data_root_test),
        pipeline=test_pipeline,
        test_mode=True,
    ),
)

val_evaluator = dict(type="AccMetric")
test_evaluator = val_evaluator

model = dict(
    cls_head=dict(num_classes=num_classes),
)

# checkpoint + 可视化 Hook
default_hooks = dict(checkpoint=dict(interval=10, max_keep_ckpts=3))
auto_scale_lr = dict(enable=False, base_batch_size=256)

custom_imports = dict(imports=["configs.hooks.vis_samples_hook"], allow_failed_imports=True)
custom_hooks = [
    dict(
        type="VisSamplesHook",
        interval=10,
        num_samples=6,
        ann_file="",
        data_root="",
        dataset_root="",
    )
]
