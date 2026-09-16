# Design: identity-action-tokenizer

> 总管：`pet-motion-latent-pipeline`（2.3 主线）。谱系调研见 video-feature-latent design L5/L6/L8。
>
> ## 谱系溯源（2026-09-16 联网精读，全部有原文出处）
>
> | 来源 | 论文 | 我们借用什么 |
> |---|---|---|
> | **TivTok** | arXiv 2606.17590（清华，2026-06） | **SIF 双 token 骨架**：TIV tokens attend 整段视频（身份），TV tokens 每帧 local scope（动作） |
> | **FLOAT** | arXiv 2412.01064（ICCV 2025） | 正交运动潜空间（继承自 LIA）；运动 latent = Σ λ_m·v_m |
> | **LIA** | arXiv 2203.09043（ICLR 2022，FLOAT 的基础） | **Gram-Schmidt 前向正交化**（硬约束）+ 加法分解（身份锚点 + 运动位移） |
> | **DeRA** | arXiv 2512.04483（西交+复旦，2025-12） | 显式对齐（外观↔图像基础模型 / 动作↔视频基础模型）+ SACP 梯度冲突处理 —— **列为可选稳定器** |
>
> **被否定的方案（记录理由）**：
> - 参考帧机制（身份只吃 1-2 帧）：TivTok §4.5 明确批评其为"hand-crafted decomposition based on reference frames"；且数据效率低
> - 纯 register tokens（Darcet 2024）：图像分割方法，无法"从整段视频整合信息"
> - 双独立编码器：误读 FLOAT；且参数量翻倍
> - 模型内 VQ 码本：由 HuBERT 式离线伪标签 CE 取代（无塌缩风险）

## 架构总图

```
原始视频（followcam / mammal_v0 / cats v1）
   │
   ▼
① 背景移除（SAM2/RVM，用现有 GroundingDINO 检测框做 prompt）
   → 猫本体 + 黑背景
   │  ※ 理由：followcam 相机随猫移动 → 背景持续变化 →
   │    TivTok 原假设"背景稳定"不成立，若不抠像，
   │    TV tokens 会把相机运动/场景变化当成"动作"学进去（污染）
   │  ※ 空间上下文（在床上/地上）已由 2.1 multi-object-detect-gate 独立处理，此处不丢信息
   ▼
② ViT 编码器（SoftVQ-VAE 风格，TivTok 口径）
   │
   ├──────────────┬──────────────────────────────┐
   ▼              ▼
TIV tokens     TV tokens
(N_TIV 个)     (每帧 N_TV 个)
attend 整段视频  只 attend 自己那帧 patch + TIV
「哪只猫」       「这一帧在动什么」
   │              │
   │              ▼
   │      FLOAT/LIA 正交运动基分解：
   │        z_t = Σ_{m=1}^{M} λ_m(t) · v_m
   │        V = {v_1..v_M} 由 Gram-Schmidt 每次前向强制正交
   │              │
   ▼              ▼
track ID InfoNCE  伪行为素 CE(CatHuBERT) + 速度匹配 + 平滑
   │              │
identity emb    λ_m(t) 基元强度序列（可解释！）
   │              │
   └──────┬───────┘
          ▼
   解码器（TIV + TV_t）→ 重建猫本体视频
   损失：L1 + perceptual + adversarial（TivTok 口径）
          ▼
   跨猫交换重建（解耦行为级验证）
```

## Decisions

### T-A1: 两阶段数据策略（先人类大数据集，后猫语料）

| 阶段 | 数据 | 规模 | 目的 |
|---|---|---|---|
| A 人类 | **UCF101**（13320 段，9.5GB，**已在 NAS**）+ 可选 K600 | 大两个数量级 | 架构可行性、重建质量、动作基元有效性——不受猫数据量制约 |
| B 猫 | 抠像后的 mammal_v0 2234 + cats v1 717 + 34 followcam | ~3k 段 | 域迁移 + 身份监督（真 track ID / 登记猫）|

阶段 A 无个体身份标注 → 只验证**架构**（重建/动作判别/正交基）；身份解耦完整验证在阶段 B。

### T-A2: 背景移除（预处理，本 change 新增）

| 项 | 决策 |
|---|---|
| 方案 | **SAM2**（首选，时序一致 + 现有检测框可作 prompt）/ RVM（备选，毛发边缘更细） |
| 输出 | 猫本体 + 黑背景（沿用项目已有"黑 margin"约定）|
| 掩码质量 | 不要求完美；特征提取对边缘误差容忍度高；但**必须消除背景运动** |
| 批处理 | 对全语料一次性生成抠像版（阶段 B 前完成）|

### T-A3: 双 token 骨架（TivTok SIF）

```
TIV tokens：每个 token 的 attention scope = 所有帧 patch + 所有 TV tokens（全局）
TV tokens：  第 t 帧 token 的 scope = 自己那帧 patch + TIV tokens + 自己（局部）

帧 t 重建 = [TIV, TV_t]（TivTok Invariant Broadcasting）
```

- 默认 `N_TIV = 16`（TivTok 实测 8 可用；我们的身份粒度要求更细，可调）
- 默认 `N_TV = 1~4`（每帧）
- **分解由架构诱导，无需显式监督**（TivTok 核心结论）

### T-A4: 动作通道——FLOAT/LIA 正交运动基（用户裁定 2026-09-16）

**机制（LIA 原文 Eq. 3，FLOAT 继承）**：
```python
# 每个前向传播：
V = gram_schmidt(V_learnable)      # V ∈ R^{M×d}，硬约束：<v_i,v_j> = δ_ij
z_t = Σ_m λ_m(t) * v_m             # 动作 latent = 正交基元的线性组合
λ(t) = V @ z_t_raw                 # 系数可闭式求解（<z_t, v_k> = λ_k）
```

- 默认 `M = 32`（正交基元数；LIA 用 20、FLOAT 用 20，我们动作更复杂可调）
- **无正交损失**——Gram-Schmidt 是前向硬约束（LIA 损失只有 L1+vgg+adv）
- **关键收益**：`λ_m(t)` 曲线 = 动作基元强度时间序列 → **行为可解释性大幅提升**；聚类可对 λ 向量做；每个 `v_m` 可单独可视化

**身份/动作分离机制**（与正交基的区别，必须分清）：
- 分离靠 **TivTok 的 attention scope**（TIV 看全段 / TV 只看本帧）
- 正交基的作用是让**运动方向互相独立可编辑**（FLOAT 的 λ-control）
- 二者叠加 = 干净解耦 + 可解释动作

### T-A5: 身份通道——TIV tokens + track ID 监督

- TIV tokens 池化 → identity embedding
- **track ID InfoNCE**：同猫不同帧/不同视频拉近，异猫推远；τ=0.07；memory bank ≥4096
- 跨视频 Re-ID 扩展：登记猫跨日视频 = 天然正样本
- 视角无关性：TIV **attend 整段视频**天然聚合多视角信息 + ReID 增强（多裁剪/随机擦除/颜色抖动）
- 可选增强：ArcFace 角度间隔头

### T-A6: 损失设计

| 通道 | 损失 |
|---|---|
| 重建 | L1 + perceptual（VGG）+ adversarial（TivTok 口径；λ₁=1, λ₂=0.2）|
| 动作 | 伪行为素 CE（CatHuBERT K=256）+ 速度匹配 + 平滑正则 |
| 身份 | track ID InfoNCE（+ 可选 ArcFace）|
| 解耦验证 | **跨猫交换重建**：猫 A 的 TV × 猫 B 的 TIV → 应重建"B 做 A 的动作" |
| 正交 | **无独立损失**（Gram-Schmidt 前向硬约束）|
| 可选稳定器 | DeRA 式对齐（外观↔DINOv3 / 动作↔V-JEPA 2 或 InternVideo2）+ SACP；仅在训练不稳时启用 |

### T-A7: 编码器初始化与训练策略

**V-JEPA 2 的定位修正（2026-09-16）**：V-JEPA 2 **不是编码器初始化**（其 latent 预测目标刻意丢弃像素细节，与重建目标方向相反）。它的位置是：
- **动作流的对齐教师候选**（DeRA 式，替代/并列 InternVideo2）
- **伪行为素标签的特征源**（CatHuBERT 迭代）
- 下游对照候选

**编码器初始化**：阶段 A 从零训 ViT（UCF-101 13320 段足够），或用 SoftVQ-VAE 开源权重（待查）。

| 阶段 | 策略 |
|---|---|
| A | UCF-101 训练（100K 迭代量级，256×256 或 128×128）；bf16 + 梯度检查点 |
| B | 继承 A 权重 → 猫语料微调 + 接入 track ID 监督 |

### T-A8: 评测矩阵

| 维度 | 指标 | 达标参考 |
|---|---|---|
| 重建 | LPIPS / PSNR / rFVD（held-out）| 与 TivTok 报告同量级 |
| 动作判别 | z_t 线性探针 top1（UCF101 101 类 / 猫 5 类）| ≥ 冻结 VideoMAE 基线 |
| **动作可解释** | λ_m(t) 基元强度曲线 + v_m 可视化 | 基元语义可控、可命名 |
| 身份检索 | identity emb 最近邻（阶段 B）| 高 |
| **视角无关性** | 同猫不同视角 identity 余弦相似度 | **≥0.7** |
| 身份泄漏 | z_t / λ 上训个体分类器 | 接近随机 |
| 解耦 | 跨猫交换重建质量 | 换身份后外观变、动作保持 |

### T-A9: 待定超参（训练时搜索）

- `N_TIV`（默认 16）、`N_TV`（默认 2）、`M`（默认 32）
- 潜维度 `d`、解码器规模、是否启用 DeRA 对齐
- 分辨率（128 vs 256）、窗口长度（16 帧）

## Risks

| 风险 | 缓解 |
|---|---|
| 抠像质量差（猫毛/遮挡）| 掩码膨胀 + 对误差鲁棒（特征级任务容忍度高）|
| 正交基在猫的大姿态变化下学不出有意义基元 | 备选：降低 M / 退化到软正交（余弦惩罚）|
| TIV tokens 抓不到"个体身份"（只抓到"猫"这个类别）| 加 track ID 监督（本设计已含）；阶段 B 实测 |
| UCF101（人类）动作基元迁移到猫 | 阶段 B 迁移实验先探；基元数可重训 |
| 训练成本（重建+对抗+双臂）| 阶段 A 先冻结部分模块跑通，再全量 |

## 谱系出处（引用规范）

- TivTok: https://arxiv.org/abs/2606.17590 （SIF §3.3、TIV 分析 §4.5）
- FLOAT: https://arxiv.org/abs/2412.01064 （Eq.8-9、§5.2 参数）
- LIA: https://arxiv.org/abs/2203.09043 （Eq.3 Gram-Schmidt、Eq.10 损失）
- DeRA: https://arxiv.org/abs/2512.04483 （§3.1-3.3）
- 本地副本：`/tmp/p_2606.17590.html`、`/tmp/float.html`、`/tmp/lia.html`、`/tmp/p_2512.04483.html`
