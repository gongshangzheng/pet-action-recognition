"""VideoMAEv2-B on the clip-indexed cat/dog behaviour dataset (ten classes)."""

_base_ = ["./cat_crop_videomaev2_raw.py"]

classes = [
    "activity", "prolonged_stationary", "eating", "drinking", "toileting",
    "grooming", "scratching", "gnawing", "fall", "seizure",
]

index_root = "datasets/cat_clip_v8"
video_root = "/home/wyy/pet-final/datasets/cat_raw"
result_root = "results/cat_clip_v8/videomaev2_b"

train_cfg = dict(max_epochs=20, val_begin=1, val_interval=2)
# 有效 batch 16：micro-batch 4 × 累积 4（accumulative_counts 属于 optim_wrapper）
optim_wrapper = dict(accumulative_counts=4)

train_dataloader = dict(
    batch_size=4,
    num_workers=6,
    dataset=dict(
        ann_file=f"{index_root}/train.jsonl",
        data_prefix=dict(video=video_root),
    ),
)
val_dataloader = dict(
    batch_size=4,
    num_workers=6,
    dataset=dict(
        ann_file=f"{index_root}/val.jsonl",
        data_prefix=dict(video=video_root),
    ),
)
test_dataloader = dict(
    batch_size=4,
    num_workers=6,
    dataset=dict(
        ann_file=f"{index_root}/test.jsonl",
        data_prefix=dict(video=video_root),
    ),
)

# 训练集类别频次：activity 2276 / prolonged 787 / eating 689 / drinking 324 /
# toileting 59 / grooming 117 / scratching 245 / gnawing 13 / fall 1 / seizure 0
# 权重取 sqrt(N/(K*n)) 并封顶 6；seizure 无样本，权重设为 0。
class_weight = [0.45, 0.76, 0.81, 1.18, 2.77, 1.96, 1.36, 5.89, 6.0, 0.0]

model = dict(
    cls_head=dict(
        num_classes=len(classes),
        loss_cls=dict(type="CrossEntropyLoss", class_weight=class_weight),
    )
)

val_evaluator = dict(classes=classes, out_file=f"{result_root}/val_metrics.json")
test_evaluator = dict(classes=classes, out_file=f"{result_root}/test_metrics.json")
work_dir = f"{result_root}/work"
