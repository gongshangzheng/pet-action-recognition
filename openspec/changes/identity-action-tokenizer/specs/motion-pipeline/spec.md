## ADDED Requirements

### Requirement: 身份-动作双 token 视频 tokenizer（研究）

系统 SHALL 提供双 token 视频重建 tokenizer：**身份 tokens**（K≈32，跨时间共享，TiTok 式瓶颈注意力）承载个体外观；**逐帧动作 latent z_t**（低维）承载运动。解码器 SHALL 以 (身份 tokens, z_t 序列) 重建视频帧；训练分两阶段（先大规模人类数据 UCF101，后猫语料迁移）。评测 MUST 覆盖：重建质量、z_t 动作判别性、e_id 身份检索、z_t 身份泄漏、跨身份交换重建。

#### Scenario: 重建验证解耦

- **WHEN** 用猫 A 的动作 z_t 序列 + 猫 B 的身份 tokens 送入解码器
- **THEN** 重建结果呈现"猫 B 做 A 的动作"——外观随身份 tokens 变、运动随 z_t 保持

#### Scenario: 动作判别性达标

- **WHEN** 冻结 tokenizer 并在标注子集上训线性探针
- **THEN** z_t 线性探针 top1 达到与冻结 VideoMAE 特征可比的水平；z_t 上的个体分类器接近随机（身份泄漏闸门）
