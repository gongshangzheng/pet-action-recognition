# Proposal: multi-object-detect-gate

> 子 change，总管：`pet-motion-latent-pipeline`（设计决策 D1/D9 见总管 design.md）

## Why

全量批处理（batch-followcam-extraction）启动前，必须验证 GroundingDINO 多 prompt 一次前向能同时正确检测多类物体（猫 + 家具），并验证「空间关系状态层」（猫在床上/桌上）规则可靠。碗/摄像头等静态小物体已实测文本检测效果差，撤下主链（走总管 D9 登记-检索路线）。

## What Changes

- GroundingDINO 多 prompt 同帧检测（默认五类：`cat. bed. table. sofa. shelf.`），正式脚本 `scripts/plf_multi_detect.py`（入版本管理）
- 空间关系状态层（规则，无学习）：猫框底边中点落入家具框 → `cat on X`，≥1.5s 迟滞防抖
- 验收视频（逐类着色打框 + 状态叠加）+ 检出统计 JSON

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 检测环节由单 prompt（cat）扩展为多 prompt（猫+家具），并新增空间关系状态输出要求

## Impact

- `scripts/plf_multi_detect.py`（新增，已入版本管理）
- 验收产物：`results/gate4/multi_detect.mp4`（5 类版，gitignore）
- 通过后：batch-followcam-extraction 的检测环节改用多 prompt，家具框 + 空间状态作为场景上下文辅助信号
