# Proposal: identity-action-tokenizer

> 子 change，总管：`pet-motion-latent-pipeline`（**2.3 主线**）。**性质：研究型**，2026-09-16 用户裁定升为主线（encoder 优先——此 change 产出编码器，下游 `video-feature-latent` / `spot-check-cli` 才能做高质量无监督工作）。

## Why

管线需要**身份与动作解耦**的猫视频编码器：身份表征表示"这是哪只猫"，逐帧动作表征表示"它在做什么"，二者可组合重建视频（验证表征完整性）与生成视频（FLOAT 同款应用）。此前障碍是猫数据量少——**解法：先在规模大两个数量级的人类动作数据集（UCF101，13320 段，已在 NAS）上验证架构，再迁移到猫语料**。

**架构（2026-09-16 联网精读三篇后收敛）**：
- **TivTok**（arXiv 2606.17590）→ 双 token 骨架：TIV tokens attend 整段视频（身份），TV tokens 每帧 local scope（动作）
- **FLOAT**（arXiv 2412.01064）/ **LIA**（arXiv 2203.09043）→ 正交运动基：z_t = Σ λ_m·v_m，基由 Gram-Schmidt 前向硬约束保证正交
- **DeRA**（arXiv 2512.04483）→ 显式对齐（可选稳定器）
- 详见 `design.md`（含被否定方案的记录与理由）

## What Changes

- **前置依赖**：`pet-background-removal`（抠像语料——消除背景运动对动作通道的污染，独立 change）
- **阶段 A（人类数据）**：UCF101 上训练 TivTok 式双 token tokenizer + 正交运动基，验证架构、重建质量、动作基元有效性
- **阶段 B（猫语料迁移）**：抠像后的猫语料继续训练，TIV 接入 track ID 监督 + 跨猫交换重建，产出解耦的双表征
- 评测：重建（LPIPS/PSNR/rFVD）、动作线性探针、λ 基元强度可解释性、身份检索、视角无关性、身份泄漏、跨猫交换重建

## Capabilities

### New Capabilities
<!-- 无新 capability -->

### Modified Capabilities

- `motion-pipeline`: 更新"身份-动作双 token 视频 tokenizer"要求——骨架由瓶颈 register tokens 改为 **TivTok SIF（TIV/TV attention scope）**，动作通道改为 **FLOAT/LIA 正交运动基（Gram-Schmidt）**，并明确抠像语料为前置条件

## Impact

- 新增 `configs/identity_action_tokenizer/` + 训练/评测脚本（`scripts/`）
- 依赖：`pet-background-removal` 产物（抠像语料）、`pet_tokenizer` 环境（conda，隔离）
- 执行机：pet（RTX 4090），GPU 任务前查占用
- 消费方：`video-feature-latent`（用产出的编码器做行为发现）、登记-检索（身份支线）、可控视频生成（远期）
- 不改变既有产出（UCF101 manifest 新增、原视频不动）
