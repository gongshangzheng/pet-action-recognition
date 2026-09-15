# Proposal: spot-check-cli

> 子 change，总管：`pet-motion-latent-pipeline`。前置：`video-feature-latent` 完成（隐空间表征可用）。

## Why

生产形态 = 非实时抽查（用户确认）：用户指定「某摄像头某时间段」→ 自动拉录像 → 预处理 → 隐码 → 动作报告。不做 7×24 实时（live 模块零改动）。

## What Changes

- `scripts/spot_check_actions.py`：抽查 CLI（动作报告 JSON/Markdown：标签/起止秒/track_id/登记身份/置信度/疑似新动作/猫在场率/空间状态段）
- `scripts/register_cats.py`：猫个体档案（登记照 → DINOv2 embedding → FAISS 检索），未登记个体标「未知猫 #N」
- 端到端联调（3 个真实时段，含 1 个无猫时段）+ L2 边界误差抽查（±1.5s）

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 抽查式推理管线行为契约（继承总管 spec，不改语义）

## Impact

- 2 个新脚本 + 猫身份特征库（gitignore）
- 与总管 D9（登记-检索架构）联调：猫 Re-ID 与物品识别共用登记-检索代码
