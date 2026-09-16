# Proposal: identity-action-tokenizer

> 子 change，总管：`pet-motion-latent-pipeline`。**性质：研究型**（对标 video-feature-latent 的条件升级路线，独立立项深入设计）。

## Why

管线最终形态需要"可控的行为潜空间"：**身份与动作解耦**的视频表征——身份 tokens 表示"这是哪只猫"，逐帧动作 latent 表示"它在做什么动作"，二者组合可重建视频（验证表征完整性），也可生成视频（验证可控性，FLOAT 同款应用）。此前的障碍是猫数据量太少（34 段 = 14.7 分钟 + 3k 短 clips）——**解法：先在规模大两个数量级的人类动作数据集（UCF101，13320 段，已在 NAS）上验证架构，再迁移到猫语料**。

**用户定义的架构（2026-09-16，FLOAT × TiTok 杂交）**：
① 从整段视频提取**几十个身份 tokens**（TiTok 式，跨时间共享）= "这是哪只猫"
② **每一帧得到一个动作 latent token** = "这一帧在动什么"
③ **解码器用 (身份 tokens + 逐帧动作 latents) 重建原始视频**——重建可行则解耦成立

## What Changes

- **阶段 A（人类数据，大规模）**：UCF101 上训练双 token 视频重建 tokenizer，验证架构 + 重建质量 + 动作 latent 判别性
- **阶段 B（猫语料迁移）**：猫语料继续训练，身份 tokens 接入 track ID 监督 + 跨猫交换重建，产出解耦的行为素/身份双表征
- 评测：重建（LPIPS/PSNR/FVD）、动作线性探针、身份检索、身份泄漏审计、跨猫交换重建

## Capabilities

### New Capabilities

- `motion-pipeline` 新增"身份-动作双 token tokenizer（研究）"要求（见 spec delta）

## Impact

- 新增 `configs/identity_tokenizer/` + 训练脚本（pet，4090；阶段 A 预计 1-2 天训练）
- 依赖：V-JEPA 2 环境（`pet_vjepa`，待建）；UCF101 在 NAS（已有）
- 消费方：video-feature-latent 的 CatHuBERT 升级路线、登记-检索（E_id 支线）、可控视频生成（远期）
