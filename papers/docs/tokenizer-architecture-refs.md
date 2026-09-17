# Tokenizer 架构参考笔记（TivTok / FLOAT-LIA / DeRA / 抠像 / 家族）

> 用途：`identity-action-tokenizer`（2.3）与 `pet-background-removal`（2.3b）的技术依据。
> 材料本地位置：`third-party/refs/`（已 gitignore）—— `papers/*.pdf`、`txt/*.txt`（PDF 转文本）、`repos/*`（浅克隆/tarball）。
> 精读日期：2026-09-16。所有结论标注出处（论文行号 = `txt/` 转文本行号；代码 = 文件:行号）。

---

## 0. 材料清单

### 论文（18 篇，`third-party/refs/papers/`）

| 文件 | arXiv | 角色 |
|---|---|---|
| `2606.17590_tivtok.pdf` | 2606.17590 | ~~骨架主源~~ → **已降为备档**（TIV/TV 双 token SIF，暂不采用；备档见 `tivtok-reference.md`）|
| `2412.01064_float.pdf` | 2412.01064 | **正交运动基主源** |
| `2203.09043_lia.pdf` | 2203.09043 | 正交基原始出处（FLOAT 继承） |
| `2512.04483_dera.pdf` | 2512.04483 | 双流 + 显式对齐（对照方案） |
| `2406.07550_titok.pdf` | 2406.07550 | 1D tokenizer 鼻祖 |
| `2412.10958_softvqvae.pdf` | 2412.10958 | **量化器主源**（软量化） |
| `2410.21264_larp.pdf` | 2410.21264 | DeRA 基座 / 可跑 1D tokenizer |
| `2412.13061_vidtok.pdf` | 2412.13061 | 重建基线 / 长视频 |
| `2505.17011_adaptok.pdf` | 2505.17011 | **建议代码基座** / 自适应 token 预算 |
| `2502.13967_flextok.pdf` | 2502.13967 | 变长 token（非商业） |
| `2602.04202_vtok.pdf` | 2602.04202 | 关键帧+残差（未开源） |
| `2505.12053_vfrtok.pdf` | 2505.12053 | 变帧率 tokenizer |
| `2408.00714_sam2.pdf` | 2408.00714 | **抠像主选** |
| `2108.11515_rvm.pdf` | 2108.11515 | 抠像备选（GPL / 人物域） |
| `2401.03407_birefnet.pdf` | 2401.03407 | 图像级抠图备选 |
| `2506.09995_vjepa2.pdf` | 2506.09995 | 对齐教师候选 |
| `2508.10104_dinov3.pdf` | 2508.10104 | 外观对齐教师 |
| `2403.15377_internvideo2.pdf` | 2403.15377 | 动作对齐教师候选 |

### 代码（14 个，`third-party/refs/repos/`）

| 目录 | 仓库 | 许可 | 状态 |
|---|---|---|---|
| `ti_tokenizer` | bytedance/1d-tokenizer（TiTok） | — | ✅ |
| `softvqvae` | Hhhhhhao/continuous_tokenizer | ⚠️ 无 LICENSE | ✅ |
| `adaptok` | VisionXLab/AdapTok | **MIT** | ✅（tarball） |
| `larp` | hywang66/LARP | **MIT** | ✅ |
| `vidtok` | microsoft/VidTok | **MIT** | ✅ |
| `lia` | wyhsirius/LIA | CC BY-NC | ✅ |
| `float` | deepbrainai-research/float | ⚠️ README 称 BY-NC-**ND**，LICENSE.md 称 BY-NC | ✅ |
| `flextok` | apple/ml-flextok | ⚠️ 双重非商业 | ✅ |
| `sam2` | facebookresearch/sam2 | **Apache-2.0** | ✅ |
| `rvm` | PeterL1n/RobustVideoMatting | **GPL-3.0** ⚠️ 传染 | ✅ |
| `birefnet` | ZhengPeng7/BiRefNet | **MIT** | ✅ |
| `vjepa2` | facebookresearch/vjepa2 | — | ✅ |
| `dinov3` | facebookresearch/dinov3 | 自定义 DINOv3 License | ✅（无权重） |
| `internvideo` | OpenGVLab/InternVideo | — | ✅ |

**无开源**：TivTok、DeRA、VTok、VFRTok（VFRTok 上游有，本地未克隆）。

---

## 1. TivTok（⬇️ 已降为备档，2026-09-17）

> **本节内容已整理并扩充到独立文档**：[`tivtok-reference.md`](./tivtok-reference.md)
>
> **状态**：TivTok 曾是骨架主源，现**暂不采用**——身份改由**参考输入**提供后，视频内 TIV 与身份通道职责重叠，SIF 的存在意义消失。主线已转向 **FLOAT**。
> 保留下方简记供快速查阅；完整版（含实现路径、论文行号、不采用理由）见上方链接。

### SIF（Scope-Induced Factorization）
- **TIV tokens**：attend 全部帧 patch + 全部 TV tokens（全局 scope，`G = [Z_TIV, Z_TV^(1..T), X_1..X_T]`）
- **TV tokens**：第 t 帧 token 只 attend 自己那帧 patch + TIV + 自己（局部，`L_t = [Z_TIV, Z_TV^(t), X_t]`）
- 出处：`txt/2606.17590_tivtok.txt` §3.3（L252–300，Eq.3/4）
- **分解由架构诱导，无显式监督**（同处 L291–295）
- **明确否定 causal mask**（L296–299：会让 TV 吸收跨帧信息，与 TIV 重叠）
- 消融代价：去掉 SIF → PSNR 19.67 / rFVD 1359.38（Table 6）

### 关键数值（论文推算，自洽）
- encoder/decoder：12 层、hidden 768、patch 4×8×8、**3D RoPE**、256×256、16 帧
- latent 维度 D：T128→128、T512→32、T1024→16
- **N_TIV : N_TV ≈ 3:1**（T128@16帧 = TIV 96 + TV 2/帧=32；T512 = 384 + 128；T1024 = 768 + 256）
- 底座 = **ViT-based SoftVQ-VAE**（2412.10958）

### 训练配方
- 损失 `L = L1 + λ1·perceptual + λ2·λ∇·adversarial`，**λ1=1、λ2=0.2**
- 判别器 **DINOv2-S**，30K iter 起；**LeCAM 0.001**
- AdamW、wd 1e-4、β=(0.9,0.95)、**global batch 64**、lr 1e-4、5K warmup、cosine、**100K iter**

### 对我们的直接影响
- ⚠️ **design 的 N_TIV=16 / N_TV=1~4 与 TivTok 最优方向相反**（应为 TIV 主导，3:1）
- SIF 必须自己实现 attention mask；**TiTok 官方代码的 attention 不支持任何 mask**（`modeling/modules/blocks.py` L85–131）→ 参考 `modeling/rar.py` L90–124 的 `attn_mask` 版 SDPA
- **TivTok 未开源**（无代码链接、未声明将发布）→ 必须自研

---

## 2. FLOAT / LIA（正交运动基）

### 正交化实现：论文说 Gram-Schmidt，代码用 QR（**非矛盾**）
- 论文（LIA `txt/2203.09043` §3.1）："implement `D_m` as a learnable matrix and **apply the Gram-Schmidt process during each forward pass**"
- **结论（2026-09-16 修正）**：**Gram-Schmidt 就是计算 QR 分解的算法**，二者是同一数学对象。论文用经典算法名描述，代码用 LAPACK 的 Householder QR（数值更稳定）。全仓库无任何 `gram_schmidt`/`parametrizations.orthogonal` 实现 → 确认就是 QR。
- **λ 由 MLP 学习**（非内积提取），因此 Q 列符号差异会被训练吸收 → 功能等价
- **需要注意的两点**：(a) Householder QR 数值稳定性优于经典 GS（代码选择的合理理由）；(b) 若要冻结基当 tokenizer 组件，需显式固定 Q 符号（代码未做）
- **代码实际**（`repos/lia/networks/styledecoder.py:439-458`）：
  ```python
  self.weight = nn.Parameter(torch.randn(512, motion_dim))
  Q, R = torch.qr(weight)          # LIA
  Q, R = torch.linalg.qr(weight)   # FLOAT（repos/float/models/float/styledecoder.py:426）
  out = torch.sum(torch.matmul(torch.diag_embed(λ), Q.T), dim=1)   # = Q @ λ
  ```
- 即 **`nn.Parameter(dim, M)` + 每次 forward 一次 QR**，无缓存、无 buffer；可学的是未约束矩阵，基 = 其 QR 像

### 分解结构
- `w_S = w_{S→r}(身份) + w_{r→S}(运动)`，`w_{r→S} = Σ_m λ_m·v_m`
- **身份分量 = 编码器输出的 512 维特征本身**（无额外模块；`repos/lia/networks/encoder.py:236,277-282`）
- **λ 由 5 层 MLP 预测**（`encoder.py:254-265`），**不是内积提取**
- 论文 Eq.15 的闭式内积（`<w, v_k> = λ_k`）**只在论文里，仓库无实现**
- 加法在 decoder 输入端：`latent = wa + directions`（`styledecoder.py:524-527`；FLOAT `FLOAT.py:59`）
- d=512、**M=20**（LIA Table 5 消融 20 最优）

### ⚠️ 移植风险（关键）
1. **去掉 warp 后没有监督驱动基指向"运动"**：LIA/FLOAT 的分解成立是因为 decoder 用 flow+warp 重建驱动帧。我们若不用 warp，必须自备解耦目标（建议：时序速度损失 + 跨身份交换一致性 + λ⊥身份 约束）
2. **λ 只有 M=20 维**：若身份信息落进这 20 维 → 泄漏（正是我们要避免的）
3. **QR 符号/相位不唯一 + 每次重算** → 基会漂移。要当 tokenizer 基用，建议**训练后固化 Q**
4. **许可**：FLOAT README 称 CC BY-NC-**ND**（禁止衍生），与 LICENSE.md（BY-NC）矛盾 → **只借鉴算法，代码自行重写**；LIA 是 CC BY-NC（可非商业衍生），但**无训练代码**

---

## 3. DeRA / LARP（对照方案）

### DeRA
- 双流：**appearance queries 256（输入第一帧）+ motion queries 768（输入整段）**，**共享同一 encoder**（各自 concat query+patch 后调用）
- 量化：`y = Quant(Za ∥ Zm)`，只量化 query 位；codebook 8192、latent 16、patch t=4/p=8、16 帧 128×128
- **显式对齐**：`L_align = −E[cos(FM_token, MLP(latent))]`，图像 FM = **DINOv3 ViT-B/16**，视频 FM = **InternVideo2-B/14**；权重 **λa=1.0, λm=0.5**
- **SACP**：`s = <g_a, g_m>`；若 `s<0` 则对称投影 `c_a = stopgrad(s/(‖g_m‖²+ε))`，`L_re^a = L_align^a − c_a·L_align^m`（ε=1e-8）
- UCF-101 上 rFVD 比 LARP 好 25%
- **未开源**

### LARP（可跑基座）
- **MIT**，权重齐全（HF `hywang66/LARP-L-long-tokenizer` 等），训练脚本齐全（`scripts/train_larp_tokenizer.sh`）
- 结构：patchify（1024 patches）→ **in-context concat + self-attention**（`models/transformer.py:62-69`，`h=cat([context,query])` 取末段）→ SVQ 量化（codebook 8192, τ=0.03）→ decoder 同构
- ⚠️ **"bottleneck attention" 在 LARP 里不存在**：其 `Bottleneck` 是线性投影+VQ，不含 attention
- 复现 DeRA 式对齐需自写：双 query 集合、encoder 中间层特征导出、FM 特征抽取与 token 数对齐、MLP 投影、对齐损失、SACP

---

## 4. 抠像选型（背景移除）

| | SAM2 | RVM | BiRefNet |
|---|---|---|---|
| 输入 | 点/**框**/mask prompt | 无需 trimap | 无 prompt（可选 box） |
| 输出 | **二值 mask**（logits>0） | alpha + fgr | 0~1 软图 |
| 时序 | **memory attention + memory bank** + 遮挡头 | ConvGRU 递归 + dtSSD 去闪 | ❌ 逐帧无时序 |
| 速度 | B+ 43.8 FPS / L 30.2 FPS（A100 1024²） | HD 104 FPS（1080Ti） | SwinL 83ms ≈ 12 FPS |
| 域 | 零样本开世界，**含野生动物评测** | **纯人类训练**（猫不可靠 ⚠️） | 类别无关 DIS，hair-level |
| 许可 | **Apache-2.0** ✅ | **GPL-3.0** ⚠️ 传染 | MIT ✅ |
| 依赖 | torch≥2.5.1 | torch==1.9（旧，冲突） | torch≥2.5 |

**结论：SAM2 为主**（box prompt 直接复用现有 GroundingDINO 检测框；memory attention 正是"背景随相机动"的解；Apache 许可干净）。
**已知弱点**：细结构（猫须）+ 快速运动易丢 → 掩码膨胀 2–3px + IoU 漂移触发中途补 prompt。
**RVM 仅作毛发边缘对照**（人物域 + GPL + 旧依赖三重否决）；**BiRefNet 作静帧/单帧质检备选**。

---

## 5. Tokenizer 家族（基座与量化器选择）

| 方案 | 结构 | 量化 | 开源 | 许可 |
|---|---|---|---|---|
| **AdapTok** | 1D 潜 token + block-causal transformer；**12L/768d/patch 4×8×8（与 TivTok 同形）** | SVQ | ✅ 代码+权重+脚本 | **MIT** |
| SoftVQ-VAE | ViT 1D token（L=32/64），仅**图像** | **SoftVQ**（τ=0.07，全可微，无码本/commit loss） | ✅ | ⚠️ 无 LICENSE |
| VidTok | 3D 卷积 VAE，栅格 5×32×32 | FSQ 或 KL | ✅ 17+5 权重 | **MIT** |
| FlexTok | ViT + register tokens，1–256 变长（图像） | 6 维 FSQ | 仅推理代码 | ⚠️ 非商业 |
| VTok | 冻结 CLIP + 冻结 DiT，只训 MLLM | 论文未说明 | ❌ | — |
| VFRTok | query-based ViT AE，连续无量化 | 无 | ✅ | MIT |

### 量化器结论（有实验证据）
- **SoftVQ 最优**：线性探针在所有 token 数下优于 VQ/AE，token 越少优势越大（SoftVQ 论文 Fig.3a）；软分配 = soft K-Means，天然适合聚类；官方有 `gmm_fit.py`
- **VQ 最差**：VidTok Table 3 显示 VQ-262144 利用率仅 **0.2%**，PSNR 23.22（塌缩）
- **FSQ**：利用率 99.8–100%，无码本学习需求 → 离散备选

**建议**：骨架 = **AdapTok 代码库（MIT）+ 自己实现 SIF mask**；~~量化器 = **SoftVQ**~~ **量化器 = 无（2026-09-17 去量化，见 §5c）**；重建基线 = VidTok；长视频分块 = VidTok v1.1。

---

## 5b. AdapTok 深读（推荐代码基座，2026-09-16 精读）

### 论文结构（`txt/2505.17011_adaptok.txt` §3.1）

> ⭐ **2026-09-17：本方案的 3D patchify 已被正式采用**（即使 SIF 已移出主线）——t 帧拼成三维体再整体切块（patch `t=4,p=8`），运动直接进 patch、token 数降 t 倍。详见 [`../../management/docs/identity-tokenizer.md`](../../management/docs/identity-tokenizer.md) §4.2 与 `identity-action-tokenizer/design.md` T-A3b。同样可借鉴：12L/768d 规模、训练配方、**block-causal attention（流式预留）**。
```
3D patchify (t×p×p) → patch embeddings e (L 个)
  ↓ Block-Causal Encoder E：e ⊕ q_enc → 块因果注意力（同块/前块可见）→ 取 latent 位输出
  ↓ Block-mask Sampler：每块随机保留前 ℓ_i 个 latent（尾部丢弃）
  ↓ SVQ 量化 → z_q
  ↓ Block-Causal Decoder D：q_dec ⊕ z_q → 取后 L 位 → 重建
```

### 代码地图
| 文件 | 内容 |
|---|---|
| `models/mask_generator.py:452+` | **`generate_attention_mask(num_img_tok_each, num_latent_each, num_groups, attn_type)`**；支持 `full_causal_type1/2/3`、`full_bi_attn`；附带 `reorder_attention_mask` / `decoder_attn_mask_with_latent_mask` / `rearrange_drop_mask` / ILP 求解 |
| `models/block.py:36-61` | `Attention.forward(x, attn_mask)`：fused SDPA 直传 + 回退 `masked_fill(~mask, -inf)` |
| `models/transformer.py:34-69` | `TransformerEncoderParallel.forward(context, query, attn_mask)` |
| `models/adaptok.py:704-711` | `encode()`：patch embed + latent query → encoder(x, q_emb, attn_mask) → bottleneck |
| `models/adaptok.py:750-761` | `decode_with_mask()`：latent_mask → decoder mask |
| `models/bottleneck.py` | SVQ（stochastic，codebook 8192，τ=0.03，commitment 0.25） |
| `cfgs/adaptok.yaml` | **12 层 / 768 hidden / 12 heads / patch t=4,p=8 / bottleneck_token_num=1024 / dim=16**（与 TivTok 同形） |
| `cfgs/adaptok.yaml` 训练 | Adam lr 1e-4 β=(0.5,0.9)、400 epochs、L1+LPIPS+GAN(transformer disc, w=0.3)+LeCAM 0.001 |

### 实现 SIF 的落地路径（**关键**）
AdapTok 的 mask 是**块因果**（同块或前块可见），而 TivTok SIF 要求 **TIV 看全部帧（含未来）** →
**不是改配置，而是新增 mask 类型**：
```
新增 attn_type = "tiv_tv"：
  TIV tokens  → 全部 patch（所有帧）+ 全部 TIV + 全部 TV   （全局，非因果）
  TV tokens(t) → 第 t 帧 patch + 全部 TIV + 自己            （局部）
```
`encoder_attn_type` / `decoder_attn_type` 是配置字符串 → 新类型可直接接入；`full_bi_attn` 可作参考实现。

## 5c. 去量化（连续 tokenizer）先例核查（2026-09-17 联网，TUN_OK）

**问题来源**：用户追问“为什么我们要在正交坐标空间里量化？”→ 结论：**不应该量化**。

### 决定性证据（逐条有源）

| # | 事实 | 来源/出处 |
|---|---|---|
| 1 | **TiTok 官方支持无 VQ 的 VAE 模式**：`quantize_mode: "vae"`，`token_size: 16`（对角高斯 + KL），`num_latent_tokens: 128` | `configs/infer/TiTok/titok_bl128_vae_c16.yaml` |
| 2 | **官方已发布 VAE 模式预训练权重**（`titok_ll32/bl64/bl128_vae_c16_imagenet`）与对应重建指标 | `README_TiTok.md` 模型表 / HF |
| 3 | **连续模式重建反而更好**：ImageNet rFID — BL-128 **VAE 0.84** vs VQ 1.49；BL-64 VAE 1.25 vs VQ 2.06；LL-32 VAE 1.61 | `README_TiTok.md` |
| 4 | TiTok 论文结论把 "**1D-VAE**" 列为 tokenizer 的泛化方向 | `txt/2406.07550_titok.txt` L1050 |
| 5 | **SoftVQ-VAE 是连续 tokenizer**：论文标题 "1-Dimensional **Continuous** Tokenizer"；`z_q = Σ p_k·c_k` 为连续加权和，前向**无 straight-through / 无 argmax**（argmax 仅用于 usage 统计） | `repos/softvqvae/modelling/quantizers/softvq.py` |
| 6 | **TivTok 基于 SoftVQ-VAE 构建** → 其“量化”本就是软的；论文虽写 "discrete code space" 但实现连续 | `txt/2606.17590_tivtok.txt` L203 / L356 |
| 7 | **MAR**（NeurIPS 2024）："discrete-valued space … is **not a necessity** for autoregressive modeling"——连续 token + 扩散损失 | arXiv 2406.11838 |
| 8 | **视频域先例**：AR Video Generation **without** Vector Quantization（非量化自回归：逐帧 + 空间集合预测） | arXiv 2412.14169 |
| 9 | **TA-TiTok** 官方声明同时处理 discrete 与 continuous token | GitHub `bytedance/1d-tokenizer` |
| 10 | FlexTok 用 **register tokens**（“外接 register tokens”的先例）| arXiv 2502.13967 |

### 术语陷阱（重要）

文献普遍把 SoftVQ 类输出仍叫 "quantized" / "discrete code space"（TivTok 原文即如此），但**实现是连续的**。
→ **不要把论文用词当成实现事实**；判断是否真离散，看代码有没有 `argmax` / straight-through。

### 为什么“正交”与“量化”不该混

```
正交性 → 基 V 的性质（M 个方向两两正交，QR 硬约束）
量化   → 系数的近似（破坏分解精度，不破坏基的正交性）
```

**数学硬限制**：R^d 中互相正交的非零向量**最多 d 个**。SoftVQ 码本 = 8192 个 32 维向量（`nn.Parameter(shape=[4, 8192, 32])`）→ **正交不可能**。
→ 所以“让码本正交”这条路在数学上就堵死了；正交只能加在 M（≈20）个基方向上。

### 去量化的代价（已知项）

| 代价 | 对策 |
|---|---|
| 失去离散词表（AR 生成用不了） | 未来生成走 flow matching（FLOAT 路线）|
| 潜空间可能各向异性 / 尺度失衡 | KL 正则（TiTok VAE 模式）+ 聚类前 whitening |
| 无码本利用率可观测 | 用 λ 方差谱 + 重激活统计 |

### 结论

> **去量化有充分先例且质量不降**；我们的“帧级离散化”需求与“行为聚类（序列级）”重叠，属于冗余 —— **v1 移除 VQ/SoftVQ**，软码本仅作备用正则器。

## 6. 对现有 OpenSpec 设计的修正清单

| # | 现有设计 | 调研结论 | 建议 |
|---|---|---|---|
| 1 | 正交基用 "Gram-Schmidt" | QR 与 Gram-Schmidt 是同一数学对象（GS 是计算 QR 的算法）；代码用 LAPACK Householder QR | 实现用 `torch.linalg.qr`；若要冻结基需固定符号 |
| 2 | `N_TIV=16, N_TV=1~4`（TIV:TV ≈ 1:2~1:8） | TivTok 最优 **TIV:TV = 3:1** | 调整为 TIV 主导，做比例消融 |
| 3 | 编码器初始化"从零训 ViT 或 SoftVQ 权重（待查）" | **SoftVQ 权重公开可得**（HF `SoftVQVAE/*`）；AdapTok MIT 可跑 | 用 SoftVQ 权重初始化 / AdapTok 代码基座 |
| 4 | V-JEPA 2 角色已修正为"对齐教师/伪标签源" | V-JEPA 2 可作动作对齐教师；DINOv3/InternVideo2 是 DeRA 实证选择 | 保留，教师候选排序：DINOv3（外观）→ V-JEPA2/InternVideo2（动作） |
| 5 | 未记录许可风险 | FLOAT **ND** 禁令、RVM **GPL** 传染、SoftVQ 仓库**无 LICENSE** | 明确"只借鉴算法/自行实现"，写入 design 风险节 |
| 6 | SIF 实现未定 | TiTok 代码无 attention mask；`rar.py` 有可参考实现 | 实现方案落成显式任务 |
| 7 | 抠像方案"SAM2/RVM 实测后定" | ~~SAM2 为默认主选~~ → **2026-09-17 改判**：抠像改用 `rembg` 类**实时小模型**（显著物体分割）；SAM 退出抠像、改用于背景对象层（关键帧）| 见 `pet-background-removal` D2 |
| 8 | 量化器 = SoftVQ | **TiTok 官方 VAE 模式（无 VQ）重建更好 0.84 vs 1.49**；SoftVQ-VAE 本就是 continuous tokenizer；MAR/AR-video 去 VQ 先例 | **全面去量化**：连续潜变量 + KL；SoftVQ 降为备用正则（2026-09-17 已调整） |

---

## 5d. OmniMate 的多参考图做法（arXiv 2607.23023，2026-07，多模态流式生成）

**它是什么**：开放域实时流式音视频生成（交互式虚拟人）。与本项目**任务不同**（它是条件生成，不是表征学习），但**参考图的用法值得借鉴**。

**MRCM（Multi-Reference Conditioning Module）机制**：

```
① 编码     每张参考图 → VAE → latent z_i^ref                        (Eq.6)
② 拼接     沿【时间维】拼在噪声视频 latent 前：
           z_t^in = [z_1^ref, …, z_N^ref, z_t]                       (Eq.7)
③ 位置编码  参考 token 用【负 RoPE】——避免占用生成帧的时间位置        (Su et al. 2024)
④ 数量     训练随机抽 4 个身份相关帧；推理最多 4 张，不足【重复补足】
```

**要点**：
- **没有融合/聚合模块**——参考图作为**额外 token 直接拼进序列**（in-context conditioning），让注意力自己使用。**"多参考图"并不需要复杂融合设计。**
- **固定 N + 不足重复**：用固定数量**规避变长参考**的工程复杂度。
- **负 RoPE** 是一个干净的"参考不占时间位"技巧。

**对我们的三条启示**：

| # | 启示 |
|---|---|
| 1 | 「多参考图」可以很轻——**in-context concat 即可**，不需要 fancy 融合模块 |
| 2 | **参考视频 ⊇ 多参考图**：从参考视频抽 N 帧即得多图 → 选 B（参考视频）天然包含 A 的能力，且覆盖视角更全 |
| 3 | **反面对照**：OmniMate **故意**让参考 token 与生成帧同处一个注意力（身份要影响生成）；而我们**禁止** patch/tubelet attend register（审计要求 λ 无身份）。**同一结构选择在两个目标下结论相反** → 隔离约束是**目标驱动**，不是通用最佳实践 |

**不能照搬的原因**：它是**条件生成**——参考图只是"条件"，不需要把身份提取成可解释、可复用的向量；我们要 λ 可解释 + 身份可复用，**必须显式分解**。
