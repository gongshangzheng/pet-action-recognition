"""VideoMAEv2-B on rendered clip windows (256x256, 60 frames, per-frame boxes)."""

_base_ = ["./cat_clip_videomaev2_b.py"]

index_root = "datasets/cat_clip_v9"
video_root = "results/cat_clip_v9/assets/clips"
result_root = "results/cat_clip_v9/videomaev2_b"

train_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=16, frame_interval=3, num_clips=1),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(256, 256), keep_ratio=False),
    dict(type="RandomResizedCrop", area_range=(0.5, 1.0)),
    dict(type="Resize", scale=(224, 224), keep_ratio=False),
    dict(type="Flip", flip_ratio=0.5),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]
eval_pipeline = [
    dict(type="DecordInit"),
    dict(type="SampleFrames", clip_len=16, frame_interval=3, num_clips=1, test_mode=True),
    dict(type="DecordDecode"),
    dict(type="Resize", scale=(256, 256), keep_ratio=False),
    dict(type="CenterCrop", crop_size=224),
    dict(type="FormatShape", input_format="NCTHW"),
    dict(type="PackActionInputs", meta_keys=("filename", "interval_start", "interval_end", "sample_id")),
]

train_dataloader = dict(
    batch_size=4, num_workers=6,
    dataset=dict(ann_file=f"{index_root}/train.jsonl", data_prefix=dict(video=video_root), pipeline=train_pipeline),
)
val_dataloader = dict(
    batch_size=4, num_workers=6,
    dataset=dict(ann_file=f"{index_root}/val.jsonl", data_prefix=dict(video=video_root), pipeline=eval_pipeline),
)
test_dataloader = dict(
    batch_size=4, num_workers=6,
    dataset=dict(ann_file=f"{index_root}/test.jsonl", data_prefix=dict(video=video_root), pipeline=eval_pipeline),
)

val_evaluator = dict(classes=classes, out_file=f"{result_root}/val_metrics.json")
test_evaluator = dict(classes=classes, out_file=f"{result_root}/test_metrics.json")
work_dir = f"{result_root}/work"
