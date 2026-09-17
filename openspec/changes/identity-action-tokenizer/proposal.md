# Proposal: identity-action-tokenizer

> 子 change，总管：`pet-motion-latent-pipeline`（**2.3 主线**）。**性质：研究型**，2026-09-16 用户裁定升为主线（encoder 优先——此 change 产出编码器，下游 `video-feature-latent` / `spot-check-cli` 才能做高质量无监督工作）。

## Why

管线需要**身份与动作解耦**的猫视频编码器：身份表征表示"这是哪只猫"，逐帧动作表征表示"它在做什么"，二者可组合重建视频（验证表征完整性）。此前障碍是猫数据量少——**解法：先在规模大两个数量级的人类动作数据集（UCF101，13320 段，已在 NAS）上验证架构，再迁移到猫语料**。

**架构（2026-09-17 定稿，主源 = FLOAT，源码级核对）**：

- **FLOAT**（arXiv 2412.01064）⭐**主源** → 整套身份-动作分解架构：`w = w_identity + Σ_m λ_m·v_m`（Eq. 8-9）；**身份来自参考输入**（独立输入流，给定而非推断）；训练 = 同片段内 S→D 重建（A.3）；损失 = L1 + VGG 多尺度感知 + 对抗
- **LIA**（arXiv 2203.09043）→ 正交基的具体实现（`torch.linalg.qr` 每前向正交化）+ 加法分解
- **参考输入**（用户裁定）→ 用户事先拍摄**单图 / 3–5 张多视角图 / 参考短视频**作身份来源；读出结构与 FLOAT 一致（卷积编码器 → 全局向量；多图/视频取平均）
- **动作读出** → 视频侧用 **3D patchify（tubelet `t=4,p=8`）**（借 AdapTok，MIT）保证运动有时序上下文
- **DeRA**（arXiv 2512.04483）→ 显式对齐（可选稳定器）
- 详见 `design.md`（含被否定方案记录、FLOAT 源码核对结论、待定项清单）

## What Changes

- **前置依赖**：`pet-background-removal`（抠像语料——消除背景运动对动作通道的污染，独立 change）
- **阶段 A（人类数据）**：UCF101 上训练 FLOAT 式身份-运动分解 tokenizer（参考可**自动构造**：同片段取一帧当参考、另一段当驱动，无需人工标注），验证架构、重建质量、动作基元有效性
- **阶段 B（猫语料迁移）**：抠像后的猫语料继续训练；接入用户提供的参考输入（每只猫一份）；产出解耦的双表征
- 评测：重建（LPIPS/PSNR/rFVD）、λ 动作线性探针、λ 基元可解释性、**双向泄漏审计**（身份→动作 / 动作→身份）、换参考验证、视角无关性

## Capabilities

### New Capabilities
<!-- 无新 capability -->

### Modified Capabilities

- `motion-pipeline`: 更新"身份-动作解耦视频 tokenizer"要求——骨架改为 **FLOAT 式参考输入 + 正交运动基**（身份来自独立参考输入、动作由 3D tubelet + QR 正交基得到），并明确抠像语料为前置条件

## Impact

- 新增 `configs/identity_action_tokenizer/` + 训练/评测脚本（`scripts/`）
- 依赖：`pet-background-removal` 产物（抠像语料）、`pet_tokenizer` 环境（conda，隔离）、**用户提供的猫参考输入**
- 执行机：pet（RTX 4090），GPU 任务前查占用
- 消费方：`video-feature-latent`（用产出的编码器做行为发现）、登记-检索（身份支线）
- 不改变既有产出（UCF101 manifest 新增、原视频不动）
