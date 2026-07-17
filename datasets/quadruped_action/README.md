# 四足动物动作数据集（占位）

这是 `server/config.py` 中 `QUADRUPED_DATASET_NAME` 指定的训练/评测数据集目录。

## 期望结构

```
datasets/quadruped_action/
├── classes.txt                       # 每行一个动作类别名
├── quadruped_action_train_list.txt   # 每行：videos_train/xxx.mp4 <label>
├── quadruped_action_val_list.txt     # 每行：videos_val/xxx.mp4 <label>
├── quadruped_action_test_list.txt    # 每行：videos_test/xxx.mp4 <label>
├── videos_train/
│   ├── xxx.mp4
│   └── ...
├── videos_val/
└── videos_test/
```

## mmaction2 适配

`scripts/train_model.py`、`scripts/run_test.py`、`scripts/inference.py` 会自动定位上述文件，并作为 `--cfg-options` 覆盖 mmaction2 config 中的 `train_dataloader.dataset.ann_file` / `data_prefix.video` 等字段。

类别数从 `classes.txt` 自动推断，并覆盖 `model.cls_head.num_classes`。

## 当前状态

数据尚未收集，`status: pending_collection`（见 `server/routers/training.py`）。
