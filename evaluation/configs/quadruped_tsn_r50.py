# 下游四足动作识别 TSN 配置（合成数据冒烟测试用）
# 不依赖 decord，改用 PyAV 后端；小分辨率以加速 CPU 训练。
# 本文件位于 evaluation/configs/，因此 _base_ 使用相对路径回到仓库根目录。
_base_ = [
    "../../third_party/mmaction2/configs/_base_/models/tsn_r50.py",
    "../../third_party/mmaction2/configs/_base_/schedules/sgd_100e.py",
    "../../third_party/mmaction2/configs/_base_/default_runtime.py",
]

# 占位，实际由 scripts/train_model.py 通过 --cfg-options 覆盖
dataset_type = "VideoDataset"
data_root = "datasets/quadruped_action/videos_train"
data_root_val = "datasets/quadruped_action/videos_val"
ann_file_train = "datasets/quadruped_action/quadruped_action_train_list.txt"
ann_file_val = "datasets/quadruped_action/quadruped_action_val_list.txt"
num_classes = 2

file_client_args = dict(io_backend="disk")

# 小分辨率 pipeline，PyAV 后端
train_pipeline = [
    dict(type="PyAVInit", **file_client_args),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3),
    dict(type="PyAVDecode"),
    dict(type="Resize", scale=(-1, 64)),
    dict(type="CenterCrop", crop_size=64),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs"),
]
val_pipeline = [
    dict(type="PyAVInit", **file_client_args),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3, test_mode=True),
    dict(type="PyAVDecode"),
    dict(type="Resize", scale=(-1, 64)),
    dict(type="CenterCrop", crop_size=64),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs"),
]
test_pipeline = val_pipeline

train_dataloader = dict(
    batch_size=2,
    num_workers=0,
    persistent_workers=False,
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
    num_workers=0,
    persistent_workers=False,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(
        type=dataset_type,
        ann_file=ann_file_val,
        data_prefix=dict(video=data_root_val),
        pipeline=val_pipeline,
        test_mode=True,
    ),
)
test_dataloader = val_dataloader

val_evaluator = dict(type="AccMetric")
test_evaluator = val_evaluator

# 关闭 ImageNet 预训练下载（冒烟测试从头训练）
model = dict(
    backbone=dict(pretrained=None),
    cls_head=dict(num_classes=num_classes),
)

# 每 epoch 都保存，方便脚本找 latest checkpoint
default_hooks = dict(checkpoint=dict(interval=1, max_keep_ckpts=3))
auto_scale_lr = dict(enable=False, base_batch_size=256)
