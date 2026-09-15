# Proposal: batch-followcam-extraction

> 子 change，总管：`pet-motion-latent-pipeline`。前置：`multi-object-detect-gate` 验收通过。

## Why

把验收通过的预处理方案（多 prompt 抽样检测 + 插值 + 平滑 + follow_adaptive 裁剪）规模化到全部 34 段白天视频，产出隐空间表征（video-feature-latent）所需的全部数据资产。已知问题：10 帧抽样间的插值框有时框不全猫——引入帧差/背景建模的逐帧框校正（用户提出）。

## What Changes

- `scripts/plf_detect_track.py`：多 prompt 抽样检测（每 10 帧）+ 插值平滑 + **逐帧运动校正**（背景建模前景 mask 修正插值框）→ 轨迹 JSON（含家具框）
- `scripts/make_followcam.py`：轨迹 → follow_adaptive 跟随视频（尺寸离群过滤内置）+ H.264 直写
- 全量 34 段批处理 + 批处理报告（检出率/插值率/校正率/离群剔除统计）

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 预处理管线新增逐帧运动校正要求与批处理报告要求

## Impact

- 新增 3 个正式脚本（入版本管理）
- 数据资产（gitignore）：`datasets/cats/followcam/`、`keypoints/`、伪标注框包、家具框轨迹
- GPU：pet plf 环境（每次用卡前 nvidia-smi 查占用）
