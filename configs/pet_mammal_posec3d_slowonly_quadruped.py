# 哺乳动物动作识别骨架配置（PoseC3D 式 SlowOnly + 17 点四足关键点）
#
# 数据：SuperAnimal-Quadruped 零样本提取 → convert_keypoints_posec3d.py 转
# PYSKL pkl（keypoint[K,T,V,C] + keypoint_score），17 点口径见
# scripts/keypoint_mapping_quadruped.json 的 canon 定义。
#
# 结构：vendor posec3d 的 SlowOnly-keypoint 管线（heatmap 输入，in_channels=17），
# 类别 7 类；左右翻转对使用四足 canon 的 6 对 L/R 关键点。
# 注意：STGCN++ 需要注册自定义骨骼 layout（vendor 只读），暂缓——见 change 设计文档。
_base_ = ["../models/mmaction2/configs/_base_/default_runtime.py"]

num_classes = 7

model = dict(
    type="Recognizer3D",
    backbone=dict(
        type="ResNet3dSlowOnly",
        depth=50,
        in_channels=17,  # 17 点四足关键点 heatmap 通道
        base_channels=32,
        num_stages=3,
        out_indices=(2,),
        stage_blocks=(3, 4, 6),
        conv1_stride_s=1,
        pool1_stride_s=1,
        inflate=(0, 1, 1),
        spatial_strides=(2, 2, 2),
        temporal_strides=(1, 1, 2),
        dilations=(1, 1, 1),
    ),
    cls_head=dict(
        type="I3DHead",
        in_channels=512,
        num_classes=num_classes,
        spatial_type="avg",
        dropout_ratio=0.5,
        average_clips="prob",
    ),
    data_preprocessor=dict(
        type="ActionDataPreprocessor",
        mean=[0.0, 0.0, 0.0],
        std=[255.0, 255.0, 255.0],
        format_shape="NCTHW_Heatmap",
    ),
)

# dataset settings（PYSKL pkl 由 convert_keypoints_posec3d.py 生成）
dataset_type = "PoseDataset"
data_root = "datasets/pet_action_mammal_v0/skeleton"
ann_file_train = "datasets/pet_action_mammal_v0/skeleton/skeleton_train.pkl"
ann_file_val = "datasets/pet_action_mammal_v0/skeleton/skeleton_val.pkl"
ann_file_test = "datasets/pet_action_mammal_v0/skeleton/skeleton_test.pkl"

# 四足 canon 17 点的 L/R 翻转对（0-based，见 keypoint_mapping_quadruped.json）
# (L_eye,R_eye) (L_earbase,R_earbase) (L_f_knee,R_f_knee)
# (L_f_paw,R_f_paw) (L_b_knee,R_b_knee) (L_b_paw,R_b_paw)
left_kp = [0, 2, 9, 11, 13, 15]
right_kp = [1, 3, 10, 12, 14, 16]

train_pipeline = [
    dict(type="DecompressPose", squeeze=True),
    dict(type="UniformSampleFrames", clip_len=48),
    dict(type="PoseDecode"),
    dict(type="PoseCompact", hw_ratio=1.0, allow_imgpad=True),
    dict(type="Resize", scale=(-1, 64)),
    dict(type="RandomResizedCrop", area_range=(0.56, 1.0)),
    dict(type="Resize", scale=(56, 56), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5, left_kp=left_kp, right_kp=right_kp),
    dict(type="GeneratePoseTarget", with_kp=True, with_limb=False),
    dict(type="FormatShape", input_format="NCTHW_Heatmap"),
    dict(type="PackActionInputs"),
]
val_pipeline = [
    dict(type="DecompressPose", squeeze=True),
    dict(type="UniformSampleFrames", clip_len=48, num_clips=1, test_mode=True),
    dict(type="PoseDecode"),
    dict(type="PoseCompact", hw_ratio=1.0, allow_imgpad=True),
    dict(type="Resize", scale=(64, 64), keep_ratio=False),
    dict(type="GeneratePoseTarget", with_kp=True, with_limb=False),
    dict(type="FormatShape", input_format="NCTHW_Heatmap"),
    dict(type="PackActionInputs"),
]
test_pipeline = [
    dict(type="DecompressPose", squeeze=True),
    dict(type="UniformSampleFrames", clip_len=48, num_clips=10, test_mode=True),
    dict(type="PoseDecode"),
    dict(type="PoseCompact", hw_ratio=1.0, allow_imgpad=True),
    dict(type="Resize", scale=(64, 64), keep_ratio=False),
    dict(type="GeneratePoseTarget", with_kp=True, with_limb=False, double=True,
         left_kp=left_kp, right_kp=right_kp),
    dict(type="FormatShape", input_format="NCTHW_Heatmap"),
    dict(type="PackActionInputs"),
]

train_dataloader = dict(
    batch_size=8,
    num_workers=4,
    persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=True),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_train,
        split="train",
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
        split="val",
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
        split="test",
        pipeline=test_pipeline,
        test_mode=True,
    ),
)

val_evaluator = dict(type="AccMetric")
test_evaluator = val_evaluator
test_cfg = dict(type="TestLoop")

# 骨架小数据：lr 放大（沿用 vendor k400-keypoint 的线性缩放惯例，bs8×单卡）
optim_wrapper = dict(
    optimizer=dict(type="SGD", lr=0.01, momentum=0.9, weight_decay=0.0001),
    clip_grad=dict(max_norm=40, norm_type=2),
)
param_scheduler = [
    dict(type="CosineAnnealingLR", T_max=120, eta_min=0, by_epoch=True),
]
train_cfg = dict(type="EpochBasedTrainLoop", max_epochs=120, val_begin=1, val_interval=5)
val_cfg = dict(type="ValLoop")

default_hooks = dict(
    checkpoint=dict(
        interval=15,
        max_keep_ckpts=1,
        save_best="auto",
        save_optimizer=False,
        save_param_scheduler=False,
    )
)
auto_scale_lr = dict(enable=False, base_batch_size=256)
