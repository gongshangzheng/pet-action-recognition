# Design: identity-action-tokenizer

> 继承总管 D3（双分解）、D5/D6；谱系调研见 video-feature-latent design L5/L6/L8（Wav2vec2/HuBERT/LatentSync/TiTok/AdapTok/Register Tokens/1d-tokenizer，2026-09-15/16 联网调研）。

## 架构总图（用户定义，FLOAT × TiTok）

```
视频段（T 帧）──骨干编码器（V-JEPA 2 fpc16 / VideoMAE，先冻结后解冻）──► patch tokens
                                                                    │
   ┌────────────────────────────────────────────────────────────────┘
   │  瓶颈交叉注意力（TiTok 式：identity tokens 作为 query 读 patch，
   │  patch 不回读 identity——压缩必须穿过这条窄缝）
   ▼
 ├─ K_id=32 身份 tokens（可学习，跨时间共享）──池化──► e_id ──► InfoNCE(track ID)
 └─ 每帧动作 query ──► z_t（32d/帧，低维瓶颈）──────────► 伪行为素 CE（CatHuBERT 迭代）
            │
   轻量解码器 G(e_id, z_1..z_T) ──► 重建视频帧
```

## Decisions

### T-A1: 两阶段数据策略（用户指定：先人类后动物）

| 阶段 | 数据 | 规模 | 目的 |
|---|---|---|---|
| A 人类 | **UCF101**（13320 段，9.5GB，**已在 NAS `/home/wyy/mnt/ucf101/UCF-101`**） | 大两个数量级 | 架构可行性、重建质量、z_t 判别性——**不受猫数据量制约** |
| B 猫 | mammal_v0 2234 + cats v1 717 + 34 followcam + 79 events | ~3k 段 | 域迁移 + 身份监督（我们的猫有登记/track ID） |

UCF101 上身份监督弱（无个体标注）→ 阶段 A 只验证**架构**（重建 + 动作判别 + token 瓶颈有效性）；身份解耦的完整验证在阶段 B（有真身份标签）。

### T-A2: 损失设计

- 重建：L1 + LPIPS（TiTok 口径；对抗损失二期可选）
- 动作判别：z_t 上的迭代伪行为素 CE（CatHuBERT，K=256）
- 身份：e_id 的 track 级 InfoNCE（阶段 B；阶段 A 用 UCF101 类别作为弱替代监督或关闭）
- 解耦三机制：身份 token dropout（10-20%）/ 跨身份交换重建 / e_id×z_t 正交惩罚
- 速度匹配 + 平滑正则（总管 D3 遗产）

### T-A3: 训练策略（4090 预算内）

- 骨干先冻结提特征（缓存 patch tokens，训练只跑瓶颈注意力+解码器——快），后期解冻末 4 层小 LR 精调
- bf16 + 梯度检查点；K_id=32、z_t=32d、解码器 ViT-S 级
- 重建目标 = **原始视频像素**（用户指定；区别于 D3 修订版的特征序列重建）
- 16 帧窗口训练、推理可滑窗

### T-A4: 评测矩阵

| 维度 | 指标 | 达标参考 |
|---|---|---|
| 重建 | LPIPS/PSNR（held-out） | 定性可用 + 与 token 数的缩放曲线 |
| 动作判别 | z_t 线性探针 top1（UCF101 101 类 / 猫 5 类） | ≥ 冻结 VideoMAE 基线的可比水平 |
| 身份检索 | e_id 最近邻检索准确率（阶段 B） | 高（身份信息该在 e_id 里） |
| 身份泄漏 | z_t 上训个体分类器 | 接近随机（动作不含身份） |
| 解耦 | 跨身份交换重建质量 | 换身份后外观变、动作保持 |

## Risks

- 冻结骨干特征缺像素细节 → 重建模糊 → 解冻末层/加大解码器（成本↑）
- z_t 塌缩吸收身份 → 身份 dropout + 交换重建 + GRL 三重防线
- UCF101 阶段学到的"动作"以人类为中心 → 阶段 B 迁移损耗（先探针量化）
