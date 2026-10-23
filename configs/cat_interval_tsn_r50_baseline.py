"""Six-class, interval-aware cat action baseline on the migrated raw videos."""

_base_ = ["../models/mmaction2/configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py"]

classes = ["common/activity", "common/eating", "common/prolonged_stationary",
           "common/drinking", "common/grooming", "abnormal/scratching"]
data_root = "datasets/cat_raw"
index_root = "datasets/cat_interval_baseline"
result_root = "results/training/cat_interval_baseline"

custom_imports = dict(imports=["petlib.datasets.cat_intervals"], allow_failed_imports=False)
model = dict(
    backbone=dict(pretrained=None, init_cfg=dict(
        type="Pretrained",
        checkpoint="checkpoints/tsn-resnet50/tsn-resnet50_pretrained.pth",
        prefix="backbone.")),
    cls_head=dict(num_classes=len(classes)),
)

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="MultiScaleCrop", input_size=224, scales=(1, 0.875, 0.75, 0.66),
         random_crop=False, max_wh_scale_gap=1),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]
eval_pipeline = [
    dict(type="DecordInit"),
    dict(type="RestrictFrameRange"),
    dict(type="SampleFrames", clip_len=1, frame_interval=1, num_clips=3, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(-1, 256)),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]

train_dataloader = dict(
    batch_size=8, num_workers=4, persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=True),
    dataset=dict(type="IntervalVideoDataset", ann_file=f"{index_root}/train.jsonl",
                 data_prefix=dict(video=data_root), pipeline=train_pipeline),
)
val_dataloader = dict(
    batch_size=8, num_workers=4, persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(type="IntervalVideoDataset", ann_file=f"{index_root}/val.jsonl",
                 data_prefix=dict(video=data_root), pipeline=eval_pipeline, test_mode=True),
)
test_dataloader = dict(
    batch_size=8, num_workers=4, persistent_workers=True,
    sampler=dict(type="DefaultSampler", shuffle=False),
    dataset=dict(type="IntervalVideoDataset", ann_file=f"{index_root}/test.jsonl",
                 data_prefix=dict(video=data_root), pipeline=eval_pipeline, test_mode=True),
)
val_evaluator = dict(type="CatIntervalMetric", classes=classes,
                     out_file=f"{result_root}/val_metrics.json")
test_evaluator = dict(type="CatIntervalMetric", classes=classes,
                      out_file=f"{result_root}/test_metrics.json")

optim_wrapper = dict(optimizer=dict(type="SGD", lr=0.001, momentum=0.9,
                                    weight_decay=0.0001),
                     clip_grad=dict(max_norm=40, norm_type=2))
param_scheduler = []
train_cfg = dict(type="EpochBasedTrainLoop", max_epochs=3, val_begin=1, val_interval=1)
val_cfg = dict(type="ValLoop")
test_cfg = dict(type="TestLoop")
default_hooks = dict(logger=dict(interval=10),
                     checkpoint=dict(interval=1, max_keep_ckpts=2,
                                     save_best="macro_f1", rule="greater"))
randomness = dict(seed=0, deterministic=False)
work_dir = f"{result_root}/work"
