## MODIFIED Requirements

### Requirement: 身份-动作双 token 视频 tokenizer（研究）

系统 SHALL 提供双 token 视频重建 tokenizer，骨架采用 **TivTok 式 Scope-Induced Factorization（SIF）**：

- **TIV tokens（时间不变，身份通道）**：attention scope MUST 覆盖整段视频的所有帧 patch（全局），承载个体身份/外观
- **TV tokens（时间可变，动作通道）**：每个 token 的 attention scope MUST 限制在本帧 patch 与 TIV tokens（局部），承载逐帧动作

动作通道 SHALL 采用 **FLOAT/LIA 式正交运动基**：动作 latent 表示为 z_t = Σ_m λ_m(t)·v_m，其中基 V = {v_m} MUST 通过 **Gram-Schmidt 前向正交化**保持正交（硬约束，非损失惩罚）。解码器 SHALL 以 (TIV, TV_t) 重建视频帧。

训练 MUST 分两阶段：**先大规模人类动作数据集（UCF101），后猫语料迁移**；猫语料 MUST 为抠像（背景移除）后的视频。评测 MUST 覆盖：重建质量、z_t 动作判别性、λ 基元可解释性、身份检索、视角无关性、身份泄漏、跨身份交换重建。

#### Scenario: 重建验证解耦

- **WHEN** 用猫 A 的动作 TV tokens 序列 + 猫 B 的 TIV tokens 送入解码器
- **THEN** 重建结果呈现"猫 B 做 A 的动作"——外观随 TIV 变、运动随 TV 保持

#### Scenario: 正交运动基有效

- **WHEN** 提取训练后的运动基 V 并计算两两内积
- **THEN** 任意两个基向量内积接近 0（<v_i, v_j> ≈ 0, i≠j），且 λ_m(t) 可闭式提取用于动作可视化

#### Scenario: 动作判别性与身份泄漏闸门

- **WHEN** 冻结 tokenizer 并在标注子集上训线性探针
- **THEN** z_t 线性探针 top1 达到可用水平；z_t / λ 上的个体分类器接近随机（身份泄漏闸门）

#### Scenario: 视角无关性

- **WHEN** 对同一只猫的不同视角/距离片段提取 identity embedding
- **THEN** 跨视角余弦相似度 MUST ≥ 0.7（低于则身份通道不达标）
