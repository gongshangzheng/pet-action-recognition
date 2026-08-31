# Proposal: integrate-frontier-models

## Why

调研（见 `papers/docs/research-landscape.md`）已明确三条高价值接入路线：① vendor 内置但未注册的 VideoMAE v1 / UniFormerV2（各约 1 小时即可获得新基线）；② 姿态桥接（SuperAnimal-Quadruped 零样本关键点 → PoseC3D 骨架识别，对家庭监控的背景/光照/遮挡变化鲁棒，零标注成本）；③ AIM 参数高效微调（数据稀缺场景的正解）。当前训练 registry 只覆盖 vendor 通用 config，这三条路都缺接入件。

## What Changes

- **注册 VideoMAE v1**（K400 掩码预训练）：新增本地 finetune config + registry 条目（vendor `configs/recognition/videomae/` 已有官方 config 与权重链接）
- **注册 UniFormerV2**：同上（vendor `configs/recognition/uniformerv2/` 已内置）
- **姿态桥接流水线**：新增 SuperAnimal-Quadruped 零样本关键点提取脚本 + PoseC3D 格式转换脚本 + 骨架动作识别 config（vendor `configs/skeleton/posec3d|stgcnpp/`），打通「宠物视频 → 关键点 → 骨架动作识别」旁路
- **AIM Adapter 微调移植**：AIM 的 Adapter 模块以 `custom_imports` 方式挂入（不改 vendor 只读目录），冻结 ViT backbone、仅训 Adapter；新增 config + registry 条目
- **文档**：接入路线图与操作说明写入 `papers/docs/research-landscape.md` 附录（或 training 文档链接）

## Capabilities

### New Capabilities

- `training-registry`: 训练 registry 条目的接入规范——config 文件约定（数据集覆盖、custom_imports、不修改 vendor）、registry 条目必填字段、骨架流水线的输入/输出格式与脚本行为、远端冒烟验证要求

### Modified Capabilities

（无）

## Impact

- **配置**：`configs/` 新增 videomae-v1 / uniformerv2 / skeleton / aim 本地 config；`configs/hooks/` 或新模块目录挂 AIM Adapter
- **脚本**：`scripts/` 新增关键点提取与格式转换脚本（远端 GPU 执行）
- **后端**：`server/routers/training.py` 的 `_MMACTION2_REGISTRY` 追加条目（纯数据追加，无接口改动）
- **训练执行**：全部训练/提取在 pet 远端（RTX 4090）进行，本地零 GPU 操作
- **Non-Goal**：VideoMAE V2 域继续预训练（二期另开 change）；InternVideo2/VideoPrism 等非 mmaction2 体系模型

## 假设记录

- SuperAnimal 关键点定义（四足 ~27 点）与 PoseC3D 动物骨架约定（参考 AP-10K 17 点）存在映射，转换脚本以 AP-10K 口径为准
- AIM 官方实现基于 VideoMAE 代码框架，Adapter 模块可直接迁移为独立模块文件
- 权重下载沿用 `scripts/download_checkpoint.py` 模式
