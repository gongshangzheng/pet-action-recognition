# TivTok / TiTok 精读简报（只读调研）

**材料**：`third-party/refs/txt/2606.17590_tivtok.txt`（831 行，全文含参考文献）、`2406.07550_titok.txt`、`refs/repos/ti_tokenizer/`；旁证：`refs/txt/2412.10958_softvqvae.txt`、`refs/repos/softvqvae/`（TivTok 的底座 SoftVQ-VAE）。
**引用约定**：txt 行号 = 纯文本提取行（双栏排版被重排，单行常混左右栏），故同时给章节号。**所有"推算"均明确标注，未标注者均为原文/代码直述。**

---

## 1. SIF 的实现方式与 TIV/TV attention scope

**原文定义（§3.3，txt L252–300）**
- TIV："each TIV token attends to all frame patches {Xt} as well as all TV tokens"（txt L252–268）
- TV："each TV token at time step t has only local visibility, restricted to its own frame patches Xt, the TIV tokens, and itself"（txt L269–271）
- 两个 key-value scope（Eq.3，txt L273–276）：
  - `G = [Z_TIV, Z_TV^(1), …, Z_TV^(T), X_1, …, X_T]`（TIV query 的全局可见集）
  - `L_t = [Z_TIV, Z_TV^(t), X_t]`（TV query 的帧局部可见集）
- 更新式（Eq.4，txt L286–289）：`Z'_TIV = Attn(Z_TIV, G)`；`Z_TV^(t)' = Attn(Z_TV^(t), L_t)`，其中 `Attn(A,B)` = A 提供 query、**只有 B 作 key/value**。
- 复杂度（txt L271–274）：`O(T²·(N_TIV+N_TV))` → `O(T²·N_TIV + T·N_TV)`。
- 关键设计意图："the TIV/TV factorization is induced by the architecture rather than imposed through explicit supervision"（txt L291–295）。
- 明确**否定 causal mask**："Using causal masking for TV tokens may appear suitable for autoregressive generation, but it would allow TV tokens to absorb cross-frame information that overlaps with the TIV tokens"（txt L296–299）。
- 消融代价：w/o SIF → PSNR 19.67 / SSIM 0.5691 / rFVD 1359.38（Table 6，txt L654–662），与 w/o IB（17.69 / 3694.34）同量级崩塌，作者称两者"mutually dependent"（txt L590–598）。

**是否用 attention mask 实现？**
- **论文全文没有出现"attention mask / masked attention"用于 SIF 的表述**（grep 全文只有 txt L563 的 "motion masks"，指被批评的 reference-frame 类方法）。官方代码未发布（见 §7），**故实现载体论文未说明**。
- 可推断的硬约束（**推断**）：两类 token 在**同一个 encoder、共享同一组层**里（Eq.3/4 是同一组更新式、且 G 包含 TV tokens，说明 TIV 与 TV 的表示在同一序列里互相可见），因此 SIF 只能通过"把某些 key/value 对屏蔽掉"实现——即 **additive/boolean attention mask，或按 query 分组的分段 attention 调用**（L_t 对每个 t 不同，无法用单个静态 mask 表达，需 block-sparse mask 或逐帧分组）。TiTok 官方代码的 attention **不支持任何 mask**（见 §6），所以这是必须自己加的部件。
- 一处歧义（**论文未说明**）：`L_t` 里的 `Z_TV^(t)` 按 Eq.3 上标写法应指"第 t 帧的整组 TV token"（即同帧 TV 之间可互看），而非仅 self；但正文措辞"and itself"（txt L270）偏 self-only。二义性会影响 mask 实现，需自行消融。

---

## 2. token 数量与维度

**原文给出的**（§4.1，txt L356–360）：encoder/decoder **12 层、hidden dim 768、patch size 4×8×8（fT=4, fW=fH=8）、3D RoPE**；训练分辨率 **256×256**；默认 **16 帧**（Table 1/3）。
- latent token 维度 D（Table 1 "#Dim."，txt L393–395）：**T128→128，T512→32，T1024→16**。
- 压缩率定义已由数据交叉验证（**推算，可靠**）：`comp_rate = #tokens × D / (3·T·H·W)`：Table 4 中 `1024×128 = 32768×4`，两者都等于 0.521%（txt L638–643）✓。

**N_TIV / N_TV 原文未直接给值 —— 以下为推算（论文未明写，但多表自洽）**

| 配置 | 16 帧（Table 1, txt L393–395） | 32 帧（Table 2, txt L435–437） | 128 帧（Table 2 L442 / Table 4 L638–643） | 推算 N_TIV | 推算 N_TV |
|---|---|---|---|---|---|
| T128 | 128 | 160 | 352 | **96** | **2 /帧**（=8 /时间 patch 组，fT=4） |
| T512 | 512 | 640 | — | **384** | **8 /帧**（=32 /组） |
| T1024 | 1024 | 1280 | — | **768** | **16 /帧**（=64 /组） |

推导链（可复核）：`tokens = N_TIV + N_TV·T`（T=帧数，与 §3.2 "Z_TV ∈ R^{T×N_TV×D}" 一致，txt L205）。T128：`128 = N_TIV + 16·N_TV`、`160 = N_TIV + 32·N_TV` → N_TV=2, N_TIV=96；32 帧 160 ✓、128 帧 `96+2·128=352` ✓（Table 4 的 1-TIV 行）。T512/T1024 用同法得 N_TIV/N_TV = 384/8、768/16，且三档**恒为 TIV:TV = 3:1**（16 帧基准）。Table 5（txt L645–652）的 TIV:TV 标注在 `total = N_TIV + 8×N_TV_per_chunk`（8 个 16 帧 chunk、TIV 跨 chunk 复用）下完全自洽：3:1→(96,32) = 352 ✓；1:1→(50,50) = 450 ✓；1:3→(25,75) = 625 ✓（450/625 由压缩率 0.229%/0.318% 反算）。
- **歧义（论文未说明）**：N_TV 是"每帧"还是"每时间 patch 组"——两种读法在数值上等价（×fT），但实现路径不同（decoder 侧要不要把同一组 TV token 复制给组内 4 帧）。

**位置编码**：**3D RoPE**（§4.1，txt L359），原文只有这一句：(t,h,w) 三轴如何切分 head dim、theta 取值、TIV/TV token 是否也吃 RoPE —— **论文未说明**。（对照：SoftVQ-VAE 原文对 latent token 用 1D 绝对位置编码、patch token 用 2D 绝对位置编码，并明确说 RoPE"left for future work"，`2412.10958` §3.1 末段 txt L219–222。）

**hidden dim 768 + 12 层** 对应 ViT-B 级（Table 7 的 Small/Base/Large 具体配置——**论文未说明**）。

---

## 3. encoder / decoder 结构 与 Invariant Broadcasting

- **底座**："built upon a ViT-based SoftVQ-VAE (Chen et al., 2025a)"（§4.1，txt L356）= arXiv 2412.10958。SoftVQ-VAE 的骨架（`2412.10958` §3.1，txt L205–222，Fig.2）：**ViT encoder-decoder** + 一组额外 1D 可学习 latent token（与 patch token 拼接进 encoder，只保留 latent 输出）+ decoder 侧 **learnable mask token** 序列回归像素。→ TivTok 把"1D latent token"一分为二成 TIV / TV 两组。
- **图注**（Fig.2，txt L261–266）：encoder 施加 SIF；压缩表示 = 共享 TIV + 逐帧 TV；decoder 用 IB 复用同一份 TIV。
- **IB（§3.4，Eq.5，txt L286–292）**：`X̂_t = D([Z_TIV, Z_TV^(t)])`，t=1…T，"all frames can be reconstructed in parallel"，**解码复杂度 O(T²)→O(T)**（txt L293–298）。
  - 实现方式（**推断，论文未写明 decoder 是否用 mask**）：把 `[Z_TIV ; Z_TV^(t)]` 与第 t 帧的 mask/patch query 拼成一条**帧内独立序列**，帧当作 batch 维即可天然并行、帧间零交叉；因此 decoder 端**不需要** mask，只需按帧切 batch。
- **跨 chunk 长视频（§3.5 + Algorithm 1，txt L303–340）**：K 个 chunk 并行编码 → **TIV 直接平均合并** `Z̄_TIV = (1/K)Σ Z_TIV^(i)`（Eq.6，txt L317–321）→ 重组 `Z = [Z̄_TIV, {Z_TV^(i,t)}]`（Eq.7）→ 全部帧按 IB 并行解码；chunk 维度复杂度 O(K²)→O(K)。收益三条：省冗余 token、降复杂度、缩短有效序列（txt L340–346）。
- **patch token 在 encoder 里的 scope**：**论文未说明**（TiTok 中 patch token 全程互相可见且最后被丢弃；TivTok 是否把 X 限制在同帧内不清楚）。

---

## 4. 训练配方（§4.1，txt L341–370）

| 项 | 值 | 出处 |
|---|---|---|
| 损失（Eq.8） | `L = L_recon + λ1·L_percept + λ2·λ∇·L_adv`，`λ∇ = ‖∇(L_recon+λ1·L_percept)‖ / ‖∇L_adv‖`（VQGAN 式自适应对抗权重） | txt L341–351 |
| 权重 | **λ1 = 1，λ2 = 0.2** | txt L353 |
| 判别器 | **DINOv2-S**，**30K iter 起**；**LeCAM = 0.001** | txt L353–355 |
| L_recon | **L1**（"incorporates L1 reconstruction loss"） | txt L349 |
| 优化器 | **AdamW，wd 1e-4，β=(0.9, 0.95)**，**global batch 64**，**base lr 1e-4**，**5K warmup**，**cosine decay** | txt L365–369 |
| 迭代 | **100K @256×256**（UCF-101+K600 混合）；长视频**再 50K 跨 chunk TIV 复用** | txt L360–364 |
| 数据 | "mixture of UCF-101 and K600"，**混合比例/采样权重/是否按长度配比 = 论文未说明** | txt L360–362 |
| 增强 | 水平翻转 + **center cropping**（原文如此，非 random crop） | txt L369–370 |
| 分辨率/长度 | 256×256；16 帧（主）/32 帧、128 帧（长视频，`128×256×256`） | Table 1/2 |
| 生成模型（非 tokenizer） | LightningDiT：hidden 1152、28 层、16 heads、patch 1、绝对位置编码；100K iter、AdamW、batch 512、lr 1e-4 常数；推理 Euler 50 步、CFG interval start 0.1、timestamp shift 2 | txt L356–365 |

**与 SoftVQ-VAE 原配方对照**（`refs/repos/softvqvae/configs/softvq-l-64.yaml` L1–60）：tau 0.07 / K=8192 / G=4 / codebook dim 32 / perceptual_weight 1.0 / disc_weight 0.2 / disc_start 20000 / dino 判别器 / lecam 0.001 / lr 1e-4 / AdamW β=(0.9,0.95) / wd 1e-4 / global batch 256 / 50 epochs / latent 64 / patch 16 / ViT-L(DINOv2 初始化)。→ TivTok 基本沿用（差异：**判别器换 DINOv2-S**、disc start 20K→30K、batch 256→64、迭代改为 100K）。**perceptual loss 用 VGG 还是 LPIPS-convnext_s：TivTok 论文未说明**（只写 "perceptual loss (Johnson 2016; Larsen 2016)"，txt L349–350）。

---

## 5. 量化方式与 codebook

- **量化方式**：§4.1 明确 "built upon a **ViT-based SoftVQ-VAE**"（txt L356）→ **软量化（连续），非硬 VQ**。
- ⚠️ **论文自相矛盾处**：§3.1/3.2 preliminary 段说 "the latent tokens are **quantized** with Q(·) … in a **discrete code space**"（txt L202–205），与 SoftVQ（连续后验加权）冲突。以 §4.1 的 SoftVQ-VAE 为准；表 1 的 #Dim.（128/32/16）与连续 latent 一致。
- **SoftVQ 机制原文**（`2412.10958` §3.2 Eq.4，txt L180–200）：`q(z|x) = Softmax(−‖ẑ−C‖²/τ)`，`z = q(z|x)·C`（**多个 codeword 的加权和**），**τ = 0.07**；且"not requiring the codebook loss or commit loss"（txt L85–87）→ **无码本塌缩/直通梯度问题**。
- **代码证据**：`refs/repos/softvqvae/modelling/quantizers/softvq.py` L7–121 `SoftVectorQuantizer`（`logits = einsum(z, embedding.detach())`、`probs = softmax(logits/tau)`、`z_q = einsum(probs, embedding)`、`compute_entropy_loss` L124–137）；**默认 codebook 设置**（`configs/softvq-l-64.yaml` L17–22）：`num_codebooks: 4`（乘积量化分段）、`codebook_size: 8192`、`codebook_embed_dim: 32`、`entropy_loss_ratio: 0.01`、`vq_loss_ratio: 0`、`commit_loss_beta: 0`。
- **TivTok 自己的 K / τ / 是否 PQ —— 论文未说明**；只能确定 latent token 维度 D ∈ {16, 32, 128}。
- 对照 TiTok（硬 VQ）：codebook 4096 / token_size 12（`configs/training/TiTok/stage2/titok_l32.yaml` L17–18）；论文口径预实验 N=1024×16ch（titok txt L368–371），主实验 N=4096（titok txt L532–534）。

---

## 6. `ti_tokenizer` 仓库可复用清单

**可直接复用**
| 文件 | 内容 | 注意 |
|---|---|---|
| `modeling/modules/blocks.py` L262–341 / L344–441 | `TiTokEncoder` / `TiTokDecoder`：patch embed(Conv2d, stride=patch) + class token + latent tokens 拼接 → ViT 层；decoder 用 `mask_token.repeat(grid²)` + latent token 拼接 | **encoder/decoder 的 attention 无任何 mask**，全双向（`Attention.forward(x)` L85–131 无 `attn_mask` 形参；`ResidualAttentionBlock.attention` L56–62 走 `self.attn(x,x,x)`）→ SIF 必须自行改造 |
| `modeling/rar.py` L90–124 + L241–242 | `Attention.forward(x, attn_mask=None)`，内部 `F.scaled_dot_product_attention(..., attn_mask=...)`，并含 `build_causal_mask` + `register_buffer` 缓存范例 | **现成的 masked-attention 实现**，是加 SIF mask 的最佳起点（把 causal mask 换成 TIV/TV block mask） |
| `modeling/titok.py` L78–180 | 模型组装：`latent_tokens = nn.Parameter(num_latent_tokens × width)`、VQ/VAE 两模式、stage1/stage2 的冻结逻辑 | 2D 图像假设 |
| `modeling/quantizer/quantizer.py` L24–119 | `VectorQuantizer`（硬 VQ + commitment_cost + `use_l2_norm` + clustering VQ）；`DiagonalGaussianDistribution` | TivTok 需 SoftVQ，改用 softvqvae 的 quantizer |
| `modeling/modules/losses.py` L68–108 / L109–260 / L46 | Stage1（proxy-code CE，**我们不需要**）/ **Stage2：L1|L2 + perceptual + hinge GAN + LeCAM + 判别器 warmup 全套** / `compute_lecam_loss` | Stage2 与 TivTok Eq.8 结构对应，是最省事的损失基座 |
| `modeling/modules/perceptual_loss.py` L28–62 | `PerceptualLoss("convnext_s")` 或 `"lpips-convnext_s-a-b"` | TivTok 未说明用哪种 |
| `modeling/modules/discriminator.py` L59 | `NLayerDiscriminator`（patch-GAN） | **不是 DINOv2-S**；DINO 判别器请用 `softvqvae/modelling/discriminators/discriminator_dino.py` |
| `utils/train_utils.py` | `create_model_and_loss_module` L101、`create_optimizer` L216、`create_lr_scheduler` L265、`train_one_epoch` L409（accelerate/EMA/wandb/grad-accum/mixed-precision 全套，1260 行） | 直接换成视频 dataloader 即可 |
| `scripts/train_titok.py` L39–173 | 训练入口 | 可复制为 `train_tivtok.py` |
| `configs/training/TiTok/stage{1,2}/*.yaml` | config 结构：`model.vq_model` / `losses` / `dataset` / `optimizer` / `lr_scheduler` / `training` | SIF 需新增 `num_tiv_tokens`、`num_tv_tokens` 等字段 |
| `modeling/titok.py::PretrainedTokenizer` L34–76 + `scripts/pretokenization.py` | 预 tokenize / 复用 MaskGIT-VQGAN 作 proxy | 图像专用 |
| `data/webdataset_reader.py`、`scripts/pretokenization.py` | wds 数据管线 / 预编码加速 | **图像专用，视频需重写** |

**SoftVQ 侧（更贴近 TivTok 底座）**
- `softvqvae/modelling/tokenizer.py`：`VQModel` L111 / `SoftVQModel` L259 / `MaskAEModel` L343（latent token + mask token + REPA 对齐的完整 tokenizer）。
- `softvqvae/modelling/quantizers/softvq.py`（见 §5）。
- `softvqvae/modelling/modules/timm_vit/rope_utils.py`（62 行）：**2D axial / mixed RoPE**（`compute_axial_cis`、`apply_rotary_emb`）；接线在 `timm_vit_models.py` L96–200（`use_rope`/`rope_mixed`/`rope_theta`）。**只有 2D，没有时间轴 → 3D RoPE 需自行扩一轴。**
- `softvqvae/modelling/discriminators/discriminator_dino.py`：DINO 判别器（TivTok 用 DINOv2-S 口径）。
- `softvqvae/train/train_tokenizer.py`、`losses/vq_loss.py`。
- **开源权重可用**（对 design.md T-A7"待查"的直接回答）：SoftVQ-L/B/BL-32/64 的 256 与 512 版权重均在 HuggingFace `https://huggingface.co/SoftVQVAE`（`softvqvae/README.md` L31、L64–73）。

**缺口（仓库里完全没有）**：任何视频/时序代码（无 `num_frames`、无时间维 patch、无 3D RoPE）、tokenizer 内 attention 的 mask 支持、DINOv2-S 判别器、（TiTok 侧的）SoftVQ 量化。

---

## 7. TivTok 是否开源？最小可行 SIF 方案

**未开源（据现有材料判断）**
- 全文（含摘要、脚注、参考文献、致谢区缺如）**没有任何代码/项目页链接**；grep `code|codebase|open-source|release|github|project page` 无命中（唯一 "open-source" 出现在参考文献里对 VidTok 的引用，txt L800）。
- 本地 `third-party/refs/repos/` 也无 tivtok 目录（16 个仓库全是竞品/official）。
- 结论：**论文未提供官方实现，也未声明"code will be released"**；必须自研。

**最小可行 SIF 实现方案（全部改动点，基于上面已定位的代码）**
1. **骨架**：以 `ti_tokenizer/modeling/modules/blocks.py` 的 ViT 堆栈为基，把 `Attention`（L85–131）替换为 `rar.py` L90–124 的 **带 `attn_mask` 版本**（SDPA 支持 bool/additive mask）。
2. **token 布局**：`seq = [X (T·H/fH·W/fW 个 patch), Z_TIV (N_TIV), Z_TV (T×N_TV)]`；TIV/TV 用可学习 1D 位置编码（SoftVQ-VAE 做法），patch token 用 **3D RoPE**（在 `rope_utils.py` 的 2D axial 基础上把 head dim 三等分为 t/h/w 三轴；TivTok 的切分方式论文未说明，需自定）。
3. **mask 构造（核心，~20 行 bool mask）**：
   - TIV query → 全部 key（patch + 所有 TIV + 所有 TV）；
   - TV query(t) → `{TIV 全体, TV_t, X_t}`（TV_t 是 self-only 还是同帧组，见 §1 歧义）；
   - patch query 的 scope **论文未说明** → 建议做两版消融：(a) 同帧内局部，(b) 与 TV 同 scope。
   实现建议：`L = (T+1+N_TIV+N_TV_total)` 级别序列，按段生成 block mask（TIV 段全 1、TV 段按帧块、patch 段按帧块），再传给 SDPA。
4. **decoder / IB**：每帧一条独立序列 `[mask tokens(H/fH·W/fW) ; Z_TIV ; Z_TV^(t)]`，**帧作 batch 维** → 无需 mask，天然并行（对齐 Eq.5）。
5. **跨 chunk 复用**：chunk 并行编码 → TIV 求平均（Eq.6）→ 重组成 Eq.7 的形式再走 4。
6. **量化**：`softvqvae/modelling/quantizers/softvq.py`（只对 latent token 做；tau=0.07、K=8192、G=4 为其默认）。
7. **损失**：照抄 `ti_tokenizer/modeling/modules/losses.py` Stage2（L109–260）+ 换入 `discriminator_dino.py`；λ1=1、λ2=0.2、LeCAM 0.001、disc start 30K。
8. **训练**：`scripts/train_titok.py` + config schema；AdamW(lr 1e-4, wd 1e-4, β=(0.9,0.95))、**global batch 64**、5K warmup、cosine、100K iter、256×256、16 帧、hflip(+center crop)。
9. **初始档位建议**：按 TivTok-T128 口径起步 = `N_TIV=96, N_TV=2/帧, D=128`（TIV:TV=3:1）；缩小规模时**保持 3:1 比例**（Table 5 显示 TV 过多显著变差：3:1→rFVD 92.09 vs 1:3→41.33… 注意该表是"分配给 TIV 越多、压缩越好但质量下降"的权衡，见 txt L620–635）。

**对现有 `openspec/changes/identity-action-tokenizer` 的三条直接提示（附带发现）**
- design T-A3 默认 `N_TIV=16, N_TV=1~4`（16 帧）→ 等于 **TIV:TV ≈ 1:2 ~ 1:8**，与 TivTok 实测最优的 **3:1** 方向相反（TivTok 的 16 帧默认量级是 TIV 96 / TV 32）。若要身份信息压进 TIV，建议 N_TIV ≥ 3×(N_TV×T) 或明确记录这一偏离并做消融。
- design 写"VGG perceptual"：TivTok 原文只写 perceptual loss，**具体网络未说明**；SoftVQ-VAE 官方配方是 `convnext_s`/LPIPS-convnext（`perceptual_loss.py` L28–62）→ 需自行决定并在 change 里落成明确参数。
- design 写"模型内 VQ 码本被否定"：TivTok 用的 **SoftVQ 是连续软量化、无 commit/codebook loss、无塌缩风险**（softvqvae txt L85–87），与"无硬 VQ"的决定**不冲突**，可作为"既保留码本归纳偏置、又避免塌缩"的折中选项。

---

## 明确"论文未说明"清单（不可臆测项）
1. SIF 的实现载体（attention mask vs 分段 attention kernel）；`L_t` 中 TV 是同帧组还是 self-only。
2. N_TIV / N_TV 的**显式**数值（本简报为从 Table 1/2/4/5 反推）。
3. 3D RoPE 的三轴切分方式、theta、是否作用于 TIV/TV token。
4. encoder 里 patch token 的 attention scope。
5. UCF-101 与 K600 的混合比例/采样策略；每卡 batch size。
6. perceptual loss 的具体网络（VGG / LPIPS / convnext_s）。
7. TivTok 自己用的 codebook K、τ、是否乘积量化；隐含的"discrete code space"与 SoftVQ 连续量化的矛盾。
8. tokenizer 的 head 数、Small/Base/Large 的层数/宽度定义。
9. 官方代码/权重（未发布、未声明）。