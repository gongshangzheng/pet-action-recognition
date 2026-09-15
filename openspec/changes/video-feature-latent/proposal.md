# Proposal: video-feature-latent

> 子 change，总管：`pet-motion-latent-pipeline`。前置：`batch-followcam-extraction` 完成（跟随视频资产就绪）。

## Why

总管关卡 0B 裁定（2026-09-14）：AP-10K 关键点在家猫特写域质量不足（conf 0.35–0.45），降级为辅助信号。动作语义的主表示改为**预训练视频编码器零训练特征**，不训练新模型；自监督 VQ 隐空间仅在零训练基线不达标时启动。

## What Changes

- 主表示选型实验：VideoMAEv2 vs DINOv2 窗口特征（16 帧窗口 stride 8）同台对比
- 胜出编码器接入 petlib（`petlib/features/` 抽象 + 契约测试）
- 全量窗口特征 → UMAP + HDBSCAN 行为簇 → 可命名率报告（用户验收节点）
- 线性探针评测：跟随视角特征 vs 原始整帧特征（主对照）
- （条件）自监督 VQ 学习版：仅当零训练基线不达标时启动

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 隐空间表征以预训练编码器零训练特征为主链；关键点降级辅助

## Impact

- `petlib/features/`（新增抽象 + 实现）
- `scripts/discover_behaviors.py`、`scripts/train_linear_probe.py`
- 特征资产（gitignore）：窗口特征 NPZ、聚类结果
