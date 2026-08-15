# cats-speedrun Tasks

## Speed Run 评测

- [x] **T1** Speed Run TSM on quadruped_cats_v1
  - Checkpoint: `/home/wyy/pet-action-recognition/results/training/work_dirs/train-tsm-resnet50-quadruped_cats_v1-1786632000/best_acc_top1_epoch_10.pth`
  - 实测指标：top1_acc=**92.1%** (93/101)，rtf=3.591，GPU 显存与宿主进程共享（同卡实测见 UCF101: 1154MB）

- [x] **T2** Speed Run SlowOnly on quadruped_cats_v1
  - Checkpoint: `/home/wyy/pet-action-recognition/results/training/work_dirs/train-slowonly-resnet50-quadruped_cats_v1-1786671053/best_acc_top1_epoch_10.pth`
  - 实测指标：top1_acc=**91.1%** (92/101)，rtf=3.691（UCF101 实测模型独占显存: 2098MB）

- [x] **T3** Speed Run TimeSformer on quadruped_cats_v1
  - Checkpoint: `/home/wyy/pet-action-recognition/results/training/work_dirs/train-timesformer-divst-quadruped_cats_v1-1786672397/best_acc_top1_epoch_1.pth`
  - 实测指标：top1_acc=**81.2%** (82/101)，rtf=3.772（UCF101 实测模型独占显存: 830MB）

> 评测方式：demo.py 单视频推理（5 类 inference config + best checkpoint），GT 取自 `datasets/quadruped_cats_v1/annotation/test_public.txt`。
> 共性错误：三个模型均有 6 个 `drinking→eating` 混淆；TimeSformer 另有 6 个 `grooming→prolonged_stationary` 混淆。
> 注：GPU 显存采样值为整卡占用（GPU0 与他人进程共享），模型独占显存以 UCF101 speedrun 实测为参考。

## 结果汇总

- [x] **T4** 更新 cats-dataset-v1 tasks.md 的 T4.1 speed run 指标
