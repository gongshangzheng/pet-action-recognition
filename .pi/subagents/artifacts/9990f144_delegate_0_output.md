已读完全部指定材料（6 篇论文 txt + 4 个仓库；AdapTok 本地 clone 损坏，改用上游 API 核验）。下面是简报。

---

# 视频 tokenizer 家族精读简报（身份-动作解耦选型用）

**本地材料根目录**：`third-party/refs/txt/`、`third-party/refs/repos/`
**行号**均指本地 `.txt` 对应的 PDF 转文本文件。

## 0. 结论速览

| 问题 | 结论 |
|---|---|
| 谁是真正的 TIV/TV 同构方案 | **TivTok**（唯一），但**未开源**，只能复现 |
| 哪个仓库最适合当"可直接跑的 1D 视频 tokenizer 底座" | **AdapTok**（MIT + 代码 + 权重 + 训练脚本，12L/768d/patch4×8×8 与 TivTok 同形） |
| 量化器该用谁 | **SoftVQ**（连续、全可微、无塌缩、线性探针最强）；FSQ 作离散备选 |
| 谁适合做重建质量参照/长视频 | **VidTok**（MIT，17+5 权重，v1.1 长视频分块）|
| 不建议 | FlexTok（图像、非商业）、VTok（未开源）、SoftVQ-VAE 原样（图像、无许可证） |

---

## 1. 基座架构对比表（含出处）

| 方案 | Backbone | Token 形态 / 数量 | 量化方式 | 视频？ | 出处 |
|---|---|---|---|---|---|
| **VidTok** | 3D 卷积 VAE；空间下采样用 2D conv、时间下采样用 1D+AlphaBlender、其余 3D conv；157M | 潜变量 **栅格 5×32×32**（17×256×256 输入，VCR 4×8×8），非 1D | 二选一：**FSQ**（隐式码本）或 **KL 连续**（4/8/16 chn） | ✅ causal / non-causal 双版本 | txt/2412.13061 88-93（Intro bullets）、232-250（Sec 3.2）、583-597（Tab 5 Model summary） |
| **SoftVQ-VAE** | **ViT** encoder/decoder（`vit_large_patch14_dinov2.lvd142m` 初始化），45M/173M/391M/608M | **1D 潜 token L=32 或 64**，dim 256 | **SoftVQ**（软分类后验，τ=0.07）→ 连续向量；码本 8192×32，num_codebooks=4（PQ） | ❌ **仅图像**（ImageNet 256/512；仓库全代码 grep "video" 零命中） | txt/2412.10958 27-30（abstract）、185-232（Sec 3.2/3.1）、244-247；repos/softvqvae/configs/softvq-l-64.yaml:20-47 |
| **AdapTok** | **block-causal 1D transformer**（encoder+decoder），12 层/768 hidden/12 heads，"AdapTok-L 195M/259M" | 1D 潜 token：patch 4×8×8→1024 patches；潜 token = **K=4 block × M=512 = 2048**，训练时按块随机丢尾、推理按预算自适应 | **SVQ 随机向量量化**（cosine-softmax → 类别采样 → STE），码本 8192 | ✅ causal | txt/2505.17011 267-300（Sec 3.1.2）、344-365（Sec 3.3 IPAL）、444-460（Sec 4.1）、757-775（Tab 8）、795-812（SVQ 细节） |
| **FlexTok** | ViT encoder with **register tokens** + rectified-flow decoder（两阶段），max 256 registers | **1D 变长 1–256 token**（图像 256×256） | **6 维 FSQ**，levels `[8,8,8,5,5,5]` → 有效词表 **64000**；nested dropout 制造有序变长 | ❌ 仅图像 | txt/2502.13967 196-260（Sec 3.1/3.2）、265-275（Stage 1）、604-606（Tab：1-256、64000）、1418 |
| **VTok** | **冻结 CLIP-L/336px 冻结视觉编码器 + 冻结 HunyuanVideo-13B DiT 解码器**，只训 MLLM | **S + (T−1)**：关键帧 16 个空间 token（4×4）+ 每帧 1 个残差 motion token（默认 6 帧/token；5s@24fps → **46 token**） | 论文**未说明**量化/码本（token 由 MLLM next-token CE 预测，视觉分支条件注入冻结 DiT） | ✅ | txt/2602.04202 288-330（Sec 3.2，Eq.13-17）、293-300（冻结项）、516-540（Tab 4/5） |
| **VFRTok** | query-based **ViT AE**（无量化），12 层/768 hidden/patch 4×8×8；3D RoPE 改**时间戳驱动** + Partial RoPE（12 头中 6 头） | **固定长度潜 token 绑定"时长"**：VFRTok-L **Z∈R^512×32**、VFRTok-S **Z∈R^128×128** | **连续 AE（无量化、无码本）** | ✅（且支持 enc/dec 异帧率） | txt/2505.12053 162-175、228-245、313-335、360-365、382-395（Tab 1）、729-750（Tab 6） |
| **TivTok** | **构建于 ViT-based SoftVQ-VAE 之上**（12 层/768 hidden/patch 4×8×8/3D RoPE） | **N_TIV + T×N_TV**：T512=512 tok/dim32、T128=128/dim128；TIV 消融 8/4/2/1，TIV:TV 比 1:3/1:1/3:1 | 论文只写 "quantized with Q(·)"，**未指明 FSQ/LFQ/VQ 具体实现**（称沿用 SoftVQ-VAE） | ✅（含跨 chunk TIV 复用） | txt/2606.17590 219-330（Sec 3.2-3.5）、373-390（Tab 1）、635-650（Tab 4/5）、354-360（Sec 4.1） |

要点：**只有 TivTok 是"视频级不变 token + 逐帧变 token"结构**；VidTok 是 3D 栅格（时间压缩 4×，逐帧分辨率会丢）；VFRTok/SoftVQ-VAE/FlexTok 是"整段 1D 潜 token"（无显式逐帧结构）；AdapTok 是"逐块 1D"（有时间局部性但非 TIV/TV 语义）。

---

## 2. 量化方式对比：SoftVQ vs VQ vs FSQ

### 2.1 机制差异

| | VQ | FSQ | SoftVQ |
|---|---|---|---|
| 后验 | 硬 argmin：`q(z=k|x)=1 if k=argmin‖ẑ−c_j‖²`（txt/2412.10958:167-171） | 每维独立 round 到 L 个固定标量值，隐式码本 `L^d`（txt/2412.13061:266-286，Sec 3.3） | **软**：`q(z|x)=Softmax(−‖ẑ−C‖²/τ)`，`z=q(z|x)C`，τ=0.07（txt/2412.10958:185-195, Eq.4） |
| 梯度 | 直通估计，**断梯度**（"Grad. Broken: yes"，txt/2412.10958:861-862） | round 的 STE；无码本可学 | **完全可微**（无需 straight-through，"No straight-through trick"，同处） |
| 额外损失 | 需 codebook loss + commit loss | 无需码本学习；只需 entropy+commit（可选） | **既不需 codebook loss 也不需 commit loss**（txt/2412.10958:288-291 "Neither codebook nor commit loss as in VQ is needed"）；KL 用 entropy 形式 `Lkl=H(q)−H(E_x q,p)`（同 844-848） |
| 代码 | repos/softvqvae/modelling/quantizers/vq.py:5-45 | repos/vidtok/vidtok/modules/regularizers.py:95-210；repos/flextok/flextok/regularizers/quantize_fsq.py | repos/softvqvae/modelling/quantizers/softvq.py:5-115（`logits→softmax(logits/τ)→z_q=Σp·C`；`compute_entropy_loss` = sample_entropy − avg_entropy） |

### 2.2 码本塌缩风险（原文硬数据）

- **VQ 塌缩最严重**：VidTok Tab 3 —— `VQ-262144` 加正则后 **利用率 U.R. = 0.2%**，PSNR 23.22 / FVD 960.5；不加正则直接 "model collapse and convergence failure"（txt/2412.13061:477-487 + 513-520）。
- **LFQ** 无正则时 U.R. 仅 **4.2%**；有正则 99.9%。
- **FSQ**：U.R. **99.8%–100%**，且"performance remaining largely unaffected even in the absence of the regularization loss term"（txt/2412.13061:483-520）。
- **SoftVQ**：无硬码本塌缩概念（软分配天然全码本参与）。码本尺寸消融：K 从 512→8192，rFID 1.82→1.03；**K=16384 反而退化到 1.23**，"an overly large codebook may harm model stability"（txt/2412.10958:1004-1010）。VQ 在高压缩下崩得更快：256→32 token 时 VQ-S rFID **1.45→10.97**，SoftVQ-S 仅 **0.80→1.24**（txt/2412.10958:417-423）。
- **KL-VAE** 的"后验塌缩（posterior-collapse）"是另一类失效（txt/2412.10958:145-156）。

### 2.3 对下游"聚类/线性探针"的友好度

| 维度 | 证据 |
|---|---|
| **SoftVQ 最优（有直接实验）** | 线性探针准确率（ImageNet-1k val）上 SoftVQ-B/BL/L **在所有 token 数下都优于 VQ-S 与 AE-S，token 越少差距越大**（txt/2412.10958:427-435, Fig.3a）。作者进一步结论："latent space quality, **reflected by linear probing accuracy**, is more closely related to the performance of the generative models"（424-426）。UMAP 显示 `ẑ`(encoder out) 与 `z`(decoder in) 之间方差极小、结构判别性强（455-462, Fig.4）。 |
| **SoftVQ 天生"聚类友好"** | 论文明确把 VQ 潜空间解释为 K-Means，SoftVQ = **soft K-Means**，可推广到 GMM；仓库直接提供 `inference/gmm_fit.py`（README "GMM Fitting"）+ `inference/cache_latent.py`，即"把潜向量做 GMM 聚类"是官方支持的用法（txt/2412.10958:178-205；repos/softvqvae/README.md GMM 段）。 |
| **FSQ 次优（间接）** | 100% 码本利用率意味着"没有死码"，离散 token 索引可直接做分类/共现聚类；但**论文未给出 FSQ 潜空间的线性探针或聚类指标** → 标注"论文未说明"，不可臆测。 |
| **VQ 最差** | 0.2% 利用率 ⇒ 绝大多数 token 映射到极少数码字，逐帧特征几乎不可分，聚类/探针会退化（由 VidTok Tab 3 利用率数据直接推出，非论文原话）。 |
| **VidTok 未提供探针实验** | VidTok 全文只有 PSNR/SSIM/LPIPS/FVD，无 linear probe / 聚类评估（txt/2412.13061 全文）→ "论文未说明"。 |

**小结**：身份通道（要线性探针/聚类）→ 用 **SoftVQ（连续）**；动作通道若要离散 token 给 AR/伪标签 → 用 **FSQ**；**避免裸 VQ**。

---

## 3. 仓库可运行性 / 权重 / 许可证

| 方案 | 本地路径 | 可运行性 | 权重 | 许可证 |
|---|---|---|---|---|
| **VidTok** | `repos/vidtok`（commit `6b18d25`，`microsoft/VidTok`） | ✅ 完整：训练 `main.py`（`--logdir`，Lightning+DDP）；推理 `scripts/inference_reconstruct.py`、`scripts/inference_evaluate.py`；配置 `configs/vidtok_*.yaml` 共 16 个 + `configs/vidtok_v1_1/` 5 个；关键模块 `vidtok/models/autoencoder.py`、`vidtok/modules/model_3dcausal.py`、`vidtok/modules/regularizers.py`（FSQ/KL） | ✅ HF `microsoft/VidTok` 实测含 **17 个 v1.0 ckpt + 5 个 v1.1 ckpt**（含 `vidtok_fsq_causal_488_32768.ckpt`、`vidtok_kl_causal_488_4chn.ckpt` 等） | **MIT**（`repos/vidtok/LICENSE`；GitHub API `license: MIT`） |
| **SoftVQ-VAE** | `repos/softvqvae`（commit `f4d60a0`，`Hhhhhhao/continuous_tokenizer`） | ✅ 完整：训练 `train/train_tokenizer.py --config configs/softvq-l-64.yaml`；推理 `inference/reconstruct_vq.py`、`inference/generate_sit.py`、`inference/gmm_fit.py`、`inference/cache_latent.py`；核心 `modelling/quantizers/softvq.py`、`modelling/tokenizer.py`。**但仅图像，无任何视频/时序模块** | ✅ HF `SoftVQVAE/softvq-{b,bl,l}-{32,64}`（8 个）+ MAETok 系列；实测 `softvq-l-64` 含 `model.safetensors`+`config.json` | ⚠️ **仓库内无 LICENSE 文件**，GitHub API `license: None` → **许可未声明**，法律上不能引用代码库，只能引方法 |
| **AdapTok** | `repos/adaptok` **本地 clone 损坏/为空**（`.git/HEAD → refs/heads/.invalid`，无 commit、无工作树）；上游 `VisionXLab/AdapTok` | ✅ 上游完整：`train.py` + `scripts/train_adaptok.sh`、`train_adaptok_scorer.sh`、`train_adaptok_ar.sh`、`train_adaptok_ar_fp.sh`、`scripts/eval_adaptok.sh` 等；目录 `models/ trainers/ ar/ cfgs/ data/` | ✅ HF `yeahhhh326/AdapTok`、`AdapTok-Scorer`、`AdapTok-AR`、`AdapTok-FP`（README 明列） | **MIT**（GitHub API `license: mit`） |
| **FlexTok** | `repos/flextok`（commit `742f53d`，已改名 `apple-aiml-research/ml-flextok`） | ⚠️ **只有推理/加载代码**：`flextok/flextok_wrapper.py`（`FlexTokFromHub`）、`flextok/regularizers/quantize_fsq.py`、`flextok/vae_wrapper.py`、`notebooks/flextok_inference.ipynb`。**仓库无 tokenizer 训练脚本**（文件清单核对无 train 入口） | ✅ HF `EPFL-VILAB/flextok_d12_d12_in1k` / `d18_d18_in1k` / `d18_d28_in1k` / `d18_d28_dfn` + 3 个 VAE（`flextok_vae_c4/c8/c16`） | ⚠️ **双重非商业**：代码 = EPFL/Apple "Sample Code License v1.1"（"for **non-commercial use**"）；权重 = Apple ML Research Model License（"exclusively for **Research Purposes**… does not include any commercial exploitation/product development"） |
| **VTok** | 无本地仓库 | ❌ **未开源**：GitHub `wangf3014/VTok` 仅 1 个 `README.md`（160 B），内容为 "Code is coming soon (waiting for internal approval)" | ❌ 无 | — |
| **VFRTok**（附） | 无本地仓库 | ✅ 上游 `KlingAIResearch/VFRTok`（原名 `KwaiVGI/VFRTok`）：`inference.py`、`train/pretrain.py`、`train/asymm.py`、`configs/`、`scripts/` | ✅ HF `KwaiVGI/VFRTok`（`vfrtok-l.bin` / `vfrtok-s.bin`） | **MIT**（GitHub API `license: MIT`） |
| **TivTok**（附） | 无 | ❌ 论文全篇无作者代码链接（grep `github` 仅命中他人引用）；GitHub 搜索无官方仓库 | ❌ | — |

---

## 4. VTok 的"关键帧+残差" vs TivTok 的 TIV/TV

### 相同点
1. **都是"加法式分解"**：把 token 总数从 `帧数 × 每帧 token` 降为 `共享部分 + 逐帧部分`（VTok 明写 "reduces the complexity … from the product of frame count and per-frame token count to **their sum**"，txt/2602.04202:28-32；TivTok 明写 `L_v = S+(T−1)` 与 `[Z_TIV, Z_TV^(1..T)]`，txt/2606.17590:210-212, 2602.04202:325-330）。
2. **共享部分承载"时空不变信息"**，逐帧部分承载"运动/位姿残差"。
3. **解码时共享部分被广播到每帧**（VTok：同一关键帧潜表示条件化所有帧；TivTok：Invariant Broadcasting `X̂_t = D[Z_TIV, Z_TV^(t)]`，txt/2606.17590:278-300）。

### 本质差异（关键）
| | VTok | TivTok |
|---|---|---|
| 不变部分的来源 | **显式第一帧**：`V^(s)=E_key(x_1)`，`x_1` 是硬指定的参考帧（txt/2602.04202:302-308） | **无参考帧**：TIV 是一组可学习 token，通过 attention scope 从**整段视频**聚合（txt/2606.17590:224-234） |
| 残差的计算 | **显式特征差**：`v_t^(m)=g_φ(F(x_t) − F(x_1))`（Eq.14） | **隐式**：TV token 只 attend 自己那帧 patch + TIV，残差性由 attention 约束**诱导**出来 |
| 解耦机制 | 手工分解（reference frame + motion residual） | **SIF（Scope-Induced Factorization）**，架构诱导，无显式监督 |
| 互补性 | VTok 适用于"理解+生成统一 MLLM"（冻结 CLIP+HunyuanVideo，只训 MLLM） | TivTok 是纯重建 tokenizer（+LightningDiT 生成），损失 L1+perceptual+adv（λ1=1, λ2=0.2，DINOv2-S 判别器，txt/2606.17590:344-352） |
| 长视频 | 无跨 chunk 机制（论文未说明） | **跨 chunk TIV 复用**（TIV 平均合并，复杂度 O(K²)→O(K)，txt/2606.17590:303-330） |

**TivTok 明确批评了 VTok 这一类做法**：把 "reference frames with motion residuals" 归入手工分解，指出 SIF "discovers what is semantically stable rather than pixel-static … distinguishes SIF from **hand-crafted decompositions based on reference frames**, motion masks, or frequency bands"（txt/2606.17590:94-101, 555-566）。其 Related Work 更点名 **SweetTok（Tan et al. 2024）"encodes the first frame and subsequent residual frames"**——与 VTok 机制几乎逐字相同（txt/2606.17590:158-166）。

### VTok 是否开源
**否**。见上表：`wangf3014/VTok` 仓库只有一句 "Code is coming soon (waiting for internal approval)"（2026-02-05 最后更新，无提交内容）。论文 Webpage 只给项目页，**正文无代码/权重承诺**（grep 全文无 "code will be released"/github 链接）。

---

## 5. AdapTok 的自适应 token 预算机制

### 机制三段式
1. **Block-mask Sampler（训练期）**：潜 token 序列按 `K=4` 个 block 划分（每 block `M=512` 上限），每次随机采样保留长度 `ℓ_i`，构造二值 mask 把每块**尾部的 token 丢掉**再送量化与解码（txt/2505.17011:286-300, Eq.1-2；训练分布：截断高斯 µ=256, σ=128, 界 [32,512]，见 444-460）。→ 模型学会"前几个 token 已经承载全局信息，越靠后越细粒度"（4.4 节 Fig.5 可视化：head tokens encode global information，568-575）。
2. **Block Causal Scorer（训练期）**：输入连续潜 `z` 与量化潜 `z_q`，**单次前向**预测当前 block 在所有候选长度 `ℓ_q` 下的质量分 `ŝ`（Eq.5）。监督信号 = 各 mask 下的**感知损失 LP**（Eq.4：复制潜序列 + 不同 mask → 计算第 q 块的 LP 作为 GT 分数）；MSE 训练（316-343）。消融：感知损失作打分指标最优（Tab 7，544-550）。
3. **IPAL（推理期）**：给定 mini-batch 平均预算 `N_b`，解 **ILP**：`min Σ ŝ_kj·b_kj s.t. Σ_j b_kj=1 ∀k, Σ j·b_kj = B·N_b`（Eq.6, Algorithm 1，344-365）。即"在总预算约束下，把 token 分给边际收益最高的样本/块"。

### 实测收益
- 自适应训练+推理三档全开最优：1024 token 时 rFVD 37.13 → **36.36**；**512 token 时 509.95 → 59.96（8.5×）**（Tab 4，473-490）。
- ILP 优于 Fixed/BiThr/BiDelta：36.36 vs 38.79/42.12/38.13（Tab 6，492-500）。
- 推理延迟 50.9 ms/video vs ElasticTok 571.7 ms（**11×**，Tab 5，500-504）；IPAL 自身只占 ~15% 时间（875-880）。
- 基线对比（UCF-101，同数据同 recipe）：AdapTok 512 tok rFVD 60 / 1024 tok 36 / 2048 tok 28，优于 OmniTokenizer†(1280 tok,94)、ElasticTok†(1022 tok,230)、CausalTok†(1024,37)（Tab 1，409-423）。

### 是否值得作为 v2 增强
**值得，但定位是"动作通道的 token 预算分配器"，不是骨干**。理由：
- 它解决的是"同样 FVD 下少用 1.8× token / 同预算下提升质量"，对我们**动作通道逐帧 token 的预算分配**直接可迁移（哪一帧的局部动作复杂 → 多给 token）；AdapTok 自己就按 block（4 帧）分配，粒度与我们"逐帧动作 token"接近。
- 但它的 causal block 设计与 **TIV 的全局 attention scope 天然冲突**（TivTok 消融显示去掉 SIF/TV 的局部 scope 会崩：w/o SIF PSNR 19.67/rFVD 1359.38，Tab 6，652-657）。所以只能把 "block-tail-drop + scorer + ILP" 当作**训练/推理调度层**叠加，不能替换 SIF。
- 风险：论文只报 UCF-101/K600（16×128×128，短片段），**未在大分辨率/长视频/猫语料验证**（论文未说明）。

---

## 6. 我们的场景（身份=整段聚合 / 动作=逐帧）该选哪套基座

> 项目现状：`openspec/changes/identity-action-tokenizer/design.md` 已收敛到 **TivTok SIF 骨架 + FLOAT/LIA 正交运动基**，并明确"编码器初始化：阶段 A 从零训 ViT …或 **用 SoftVQ-VAE 开源权重（待查）**"。本次调研正好填这个"待查"。

### 推荐（按优先级）

**① 骨架基座 = AdapTok 代码库（`VisionXLab/AdapTok`，MIT）+ 改写 attention mask 实现 TivTok SIF**
- 理由（可验证）：AdapTok 是唯一"**1D 潜 token 空间 + block-causal transformer + 训练脚本 + 权重 + MIT**"的视频 tokenizer；超参与 TivTok 同形（12 层/768 hidden/patch 4×8×8，txt/2505.17011:757-775 vs txt/2606.17590:354-360），把 `M` 换成"TIV 全局 scope + TV 局部 scope"的 mask 即可得到 SIF（TivTok §3.3 的 mask 设计给得很完整，2606.17590:219-300）。
- 需要改动：AdapTok 的 block-causal 是**纯因果**，而 TIV 必须看全段 —— 把 TIV 行改为全可见（这正是 TivTok 的要求："a token intended to capture temporal invariants must see the entire sequence"2406.17590:224-228）。
- 同时可白拿它的 **scorer + IPAL** 作为动作通道预算调度（见 §5）。

**② 量化器 = SoftVQ（移植 `repos/softvqvae/modelling/quantizers/softvq.py`）+ 用 SoftVQ-VAE 权重初始化 ViT**
- 理由：身份通道要做线性探针/聚类/身份检索，**只有 SoftVQ 有实验证据表明探针精度全面优于 VQ/AE 且低 token 数下优势更大**（txt/2412.10958:427-435）；且软分配 = soft K-Means，天然适合"行为基元聚类"，还直接有 `gmm_fit.py` 工具。全可微 ⇒ REPA 式对齐（外观↔DINOv3）能直接作用到 encoder（SoftVQ 论文明确 VQ 因断梯度做不了这件事：877-888），这与我们 design 里"动作↔V-JEPA2/DINOv3 对齐"的可选稳定器吻合。
- 注意：SoftVQ 是无许可证仓库 → **只移植算法/自写实现，不直接复制代码**；权重（HF `SoftVQVAE/*`，纯 safetensors）用于初始化更干净。另：`softvq-l-64` 的 config 里 `repa: false`，没有对齐训练，**其权重 vs 论文 Fig.3 的探针结论不能直接划等号**（这是我要提醒的坑）。

**③ 重建质量参照/长视频 = VidTok（MIT）**
- 用作 (a) 重建上界基线（FSQ-262144 PSNR 29.82 vs 我们的 TivTok 式重实现）；(b) **v1.1 的长视频分块推理（`chunk_size` + `read_long_video`，README 32-49）可直接借用**——我们 followcam 长片段需要"任意长度平滑 tokenize"；(c) 其两阶段训练（低分辨率预训练 + 只微调 decoder）在 4090 上省一半算力，是现成 recipe（2412.13061:106-115）。
- 但它**不适合当身份-动作骨架**：潜变量是 5×32×32 栅格 + 时间压缩 4×，"逐帧动作"的时间分辨率先天损失；要加 TIV 聚合需另写 head。

**④ 动作通道的备选基座 = VFRTok（MIT，有 l/s 权重）**
- "时长正比信息量假设 + 固定长度潜 + 异帧率 enc/dec"（txt/2505.12053:228-245, 302-310）与我们"动作应与时长而非帧数挂钩"的判断一致，能处理猫语料里混杂帧率；连续无量化，适合做 FLOAT/LIA 正交基的输入。可作为**动作通道的对照实验臂**，不作为主线。

### 不推荐
- **FlexTok**：图像域 + 代码/权重双重非商业 + 无训练脚本 → 仅可作"变长/粗到细有序 token"的**方法论参考**（nested dropout 思想，2502.13967:240-260）。
- **VTok**：无论文级实现，代码未放（"waiting for internal approval"），且 TivTok 已论证其手工参考帧分解弱于 SIF。
- **SoftVQ-VAE 原样**：仅图像、无时序模块、无许可证。

---

## 7. 不确定 / 论文未说明项（不臆测）

1. **TivTok 的量化器具体是什么**：只写 "quantized with Q(·)" + "built upon SoftVQ-VAE"（2606.17590:205, 214, 356），**未说明是 SoftVQ 软分配还是 VQ/LFQ**。→ "论文未说明"。
2. **VTok 的 token 是否离散/有无码本**：正文只给 MLLM 的 next-token CE（Eq.10, 2602.04202:270-278）+ 条件注入冻结 DiT，**无 VQ/FSQ/码本描述**。→ "论文未说明"。
3. **FSQ 潜空间的线性探针/聚类指标**：VidTok 与 FlexTok 都只报 PSNR/SSIM/LPIPS/FVD/rFID/FID，**无 linear probe 或聚类实验**。→ "论文未说明"。
4. **AdapTok 是否支持非因果 / 高分辨率**：全部实验为 16×128×128 因果（2505.17011:448-451）；256×256 与长视频未验证。→ "论文未说明"。
5. **SoftVQ-VAE 在视频上的可行性**：仓库零视频代码，论文零视频实验。移植到视频属**我们的工程推断**，无文献支持。
6. **AdapTok 许可证与文件内容**：本地 clone 为空，我用 GitHub API + raw README 核验（MIT、scripts 列表、HF 权重链接），**未逐行读代码**；训练脚本内容未核。
7. 本次未读 `2406.07550_titok.txt`（TiTok 原文）与 `2506.09995_vjepa2`，若需要 TiTok 的 register/1D 细节对比需补读。

---

## 8. 证据索引（快速跳转）

| 主题 | 文件:行 |
|---|---|
| VidTok 架构/量化/训练 | `txt/2412.13061_vidtok.txt`:88-93、232-250、266-286、288-320、477-520、583-597、106-115 |
| SoftVQ 机制/损失/码本 size | `txt/2412.10958_softvqvae.txt`:145-156、185-205、288-291、417-426、427-435、844-848、860-890、1004-1010 |
| AdapTok 机制 | `txt/2505.17011_adaptok.txt`:267-300、316-343、344-365、409-423、444-460、473-504、757-812 |
| FlexTok | `txt/2502.13967_flextok.txt`:196-260、265-275、604-606、1012、1418 |
| VTok | `txt/2602.04202_vtok.txt`:28-32、288-330、293-300、516-540 |
| VFRTok | `txt/2505.12053_vfrtok.txt`:162-175、228-245、302-310、360-365、382-395、729-750 |
| TivTok | `txt/2606.17590_tivtok.txt`:94-101、158-166、219-330、344-360、373-390、555-575、635-660 |
| 代码 | `repos/softvqvae/modelling/quantizers/softvq.py`:5-115；`repos/vidtok/vidtok/modules/regularizers.py`:95-210；`repos/vidtok/configs/vidtok_fsq_causal_488_32768.yaml`:34-40；`repos/flextok/flextok/regularizers/quantize_fsq.py` |