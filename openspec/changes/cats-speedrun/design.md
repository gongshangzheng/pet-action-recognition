# cats-speedrun Design

## Speed Run 执行方式

### 工具
`scripts/speedrun.py` — 批量推理脚本，调用 `scripts/inference.py` 对视频做推理 + cv2 标注输出。

### 命令模板

```bash
ssh pet "cd ~/pet-action-recognition && CUDA_VISIBLE_DEVICES=1 ~/miniconda3/envs/pet/bin/python scripts/speedrun.py \
  --model-id <model_id> \
  --dataset-id quadruped_cats_v1 \
  --split test \
  --work-dir results/speedrun/cats-<model_id> \
  --run-id speedrun-cats-<model_id> \
  --checkpoint <best_ckpt_path> \
  --annotate \
  --output-dir results/speedrun/cats-<model_id>"
```

### Checkpoint 路径（pet 上）

| 模型 | Run ID | Best checkpoint |
|------|--------|----------------|
| TSM | `train-tsm-resnet50-quadruped_cats_v1-1786632000` | `best_acc_top1_epoch_10.pth` |
| SlowOnly | `train-slowonly-resnet50-quadruped_cats_v1-1786671053` | `best_acc_top1_epoch_10.pth` |
| TimeSformer | `train-timesformer-divst-quadruped_cats_v1-1786672397` | `best_acc_top1_epoch_1.pth` |

Base: `/home/wyy/pet-action-recognition/results/training/work_dirs/<run_id>/best_acc_top1_epoch_*.pth`

### GPU 选择

使用 GPU 1（当前空闲）：
```bash
CUDA_VISIBLE_DEVICES=1
```

### 预期输出

- `results/speedrun/results.json` 更新（追加 cats 条目）
- `results/speedrun/cats-<model_id>/` 输出目录含标注视频
