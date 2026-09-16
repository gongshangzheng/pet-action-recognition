## 材料与环境状态（先说明证据来源）

| 项 | 状态 |
|---|---|
| `third-party/refs/txt/2512.04483_dera.txt` | 582 行，**仅正文+参考文献，无 Appendix**（`grep -i appendix` 无命中）→ 很多实现细节无法从本地文本确认 |
| `third-party/refs/txt/2410.21264_larp.txt` | 1319 行，ICLR 2025 版（v2, 2025-06-16），含 Appendix |
| `third-party/refs/repos/larp/` | **本地 clone 是坏的**：只有 `.git/`，`HEAD=refs/heads/.invalid`，`objects/pack/tmp_pack_XVC8hB`（33 MB，截断）；工作区文件不存在 |
| 我采用的读码方式 | 把该 pack 复制到 `/tmp/larp_pack/` 后 `git unpack-objects` 抢救 → 得到 **53/54 个文件**，落在 `/tmp/larp_src/`（未改动项目内任何文件）。恢复出的 commit = `8aaed63354c8c0fabcb8a86a2e31c34320e6db86`，经 GitHub API 核对**就是当前 HEAD**（2025-02-11 "Update README.md"，shallow，父提交 8849d4b 不在 pack 内） |
| 未恢复的 2 个文件 | `utils/statistics.py`（77 行，纯 python 指标函数，已从 GitHub raw 取回核对）、`utils/fvd/i3d_torchscript.pt`（二进制 FVD 权重，源码在 `utils/fvd/fvd.py:328-329` 给的是 dropbox 下载地址） |
| DeRA 代码 | **本地不存在 DeRA 仓库**（`third-party/refs/repos/` 下无 dera；grep 命中的都是无关文件）→ 第 6 条里"缺什么"包含了整个 SACP/对齐实现 |

下文所有 `文件:行` 中，代码行号指 `/tmp/larp_src/<path>`（内容与 GitHub HEAD 8aaed63 一致）；论文行号指 `third-party/refs/txt/*.txt` 的行号。

---

## 1. DeRA 双流结构细节

**Token 数**（确定性数据）
- appearance queries `Qa ∈ R^{La×d}`、motion queries `Qm ∈ R^{Lm×d}`，`L = La + Lm` 为最终离散 token 总数 —— `dera.txt:171-174`
- 具体数值：**appearance = 256，motion = 768，合计 1024** —— `dera.txt:308`（"We set the number of appearance and motion tokens to 256 and 768, respectively"）；对应 Table 1 的 `Tokens=1024`、`Codebook=8192`（`dera.txt:281-282`）
- 隐藏维 768、latent 维 16、codebook 8192 —— `dera.txt:309`；patch 尺寸 `t=4, p=8`，16 帧 / 128×128 —— `dera.txt:306-307`

**两路输入与 patchify**（`dera.txt:145-155`）
- appearance 路输入 **第一帧 x0**；motion 路输入 **整段 x**；
- 两个线性层把 x0 patch（p×p）和 x（t×p×p）投影为 `Es ∈ R^{Ls×d}`、`Et ∈ R^{Lt×d}`，其中 `Ls = H/p × W/p`、`Lt = T/t × H/p × W/p`。代入 p=8, t=4, 128×128, 16 帧：**Ls = 256（首帧 patch 数），Lt = 4×16×16 = 1024（整片段 patch 数）**

**"共享 encoder" 怎么实现**（`dera.txt:162-186`）
- 论文原话："both streams share the same encoder to ensure computational efficiency"（`dera.txt:167`）
- 公式 (1)：`Za ∥ Ea = E(Qa ∥ Es)`，`Zm ∥ Em = E(Qm ∥ Et)` —— 即**每一路各自把 query 与自己那路的 patch embedding 拼接，然后调用同一个 encoder E（权重共享）**，输出为 `[query 位输出 ∥ patch 位输出]`。
- 论文**没有说明**是"两路各做一次前向"还是"拼成一个长序列一次前向"（也不会影响结果，因为都是同一个 in-context 拼接式 transformer）。注意 DeRA 写作 `Q∥E`（query 在前），而 LARP 参考实现是 `[context(patch), query]`（query 在后，取最后 query_length 个 token）——`models/transformer.py:62-69`。这是复现时必须决定的实现细节（论文/代码未统一）。
- 论文明确 "we employ vanilla transformer blocks for both the encoder and decoder" —— `dera.txt:164-165`（即 LARP 的 `transformer_encoder_parallel` 同款：timm `Block` 堆叠 + in-context 拼接）。

**拼接后如何量化**（`dera.txt:186-200`）
- 只有 **query 位输出**参与量化：`y = Quant(Za ∥ Zm)`，`y ∈ R^{L×dz}`，L=1024（Eq 2）。即量化前在 token 维上拼成 256+768=1024。
- 量化器写作 VQ-VAE 的 `Quant(·)` [28]（`dera.txt:187`、`248-250`），**未说明是否采用 LARP 的 stochastic VQ（SVQ）**——论文/代码未说明；DeRA 只报了 codebook 8192、latent dim 16。
- 解码器：`Zd = D(Qd ∥ y)`，取 `Zd[1:Ld]` reshape 回视频（Eq 3，`dera.txt:192-200`）；**Ld 的数值论文未给**。注：LARP 里 decoder 侧 patch query 数为 1024（4×16×16，`models/larp_tokenizer.py:109-115` + `cfgs/larp_tokenizer.yaml:77-78`）。

> 对我们的意义：DeRA 保持总 token 数 1024 不变（与 LARP 同压缩率），只是把 1024 切分成 **256 外观 / 768 动作（1:3）**。这是一个可直接照搬的默认比例，且 `dera.txt:299-304` 图 3 提供了 512/768/1024 总预算的对比。

---

## 2. 显式对齐损失的具体形式

**损失形式**（`dera.txt:226-241`，Eq 4）
- 就是逐 token 的**负余弦相似度**，对 batch 与 token 求均值：
  - `L_a^align = −E[ (1/Ls) Σ_{n=1..Ls} (E_n^{ifm}·h_φ(E_n^a)) / (‖E_n^{ifm}‖‖h_φ(E_n^a)‖) ]`
  - `L_m^align = −E[ (1/Lt) Σ_{n=1..Lt} (E_n^{vfm}·h_φ(E_n^m)) / (‖E_n^{vfm}‖‖h_φ(E_n^m)‖) ]`
- 目标 token：`E^{ifm}` = 图像基础模型 token，`E^{vfm}` = 视频基础模型 token（`dera.txt:241-242`）
- 被对齐的 latent：原话 "DeRA aligns the latent embeddings **Ea, Em of the encoder (in Eq. (1))**"（`dera.txt:216`）。注意 Eq (1) 里 `Ea/Em` 是**encoder 输出的 patch 位 embedding**，`Za/Zm` 才是被量化的 query 位输出。**求和上限是 Ls=256 / Lt=1024**，与 patch 位输出个数一致、与 query 数（256/768）不一致（motion 路 768≠1024）→ 证据支持"对齐的是 patch 位输出"，但论文用词（"latent embeddings"）含糊；**query 位是否也对齐，论文未说明**。另外 La=256 恰好等于 Ls=256，外观路的指代无法从论文区分。

**目标模型与取特征层**
- DINOv3 **ViT-B/16** [18]（图像）、InternVideo2-**B/14** [35]（视频） —— `dera.txt:311-313`
- 取层：Table 6（`dera.txt:407-426`）测了 Depth = 6/8/10/12；caption 写 "Depth denotes **the encoder layer index** whose features will be aligned"（`dera.txt:425-426`），正文说 "the **final encoder layer** (Depth = 12) yielding the best results"（`dera.txt:412`）。
  ⚠️ **歧义**：这句话分不清 Depth=12 指 "DeRA tokenizer encoder 的第 12 层" 还是 "FM 的第 12 层"（DINOv3 ViT-B/16 与 InternVideo2-B/14 都是 12 层；LARP/DeRA tokenizer encoder 默认也是 depth 12，见 `cfgs/larp_tokenizer.yaml:84`）。**FM 目标特征取自哪一层，论文未明确说明**。若按 REPA 系列惯例（[37][46] 被 DeRA 引用，`dera.txt:311`）应是"tokenizer encoder 中间层 ↔ 冻结 FM 最后一层"。

**MLP 投影**
- "A lightweight **two-layer MLP h_φ** projects the latents into the target latent space"（`dera.txt:220-222`）；两路在公式中都用同一符号 `h_φ`，**是否共享权重、隐层宽度、是否含 LayerNorm，论文/本地文本未说明（无 Appendix）**。

**损失权重**（`dera.txt:243-250`，Eq 5）
- 总损失 `L = λa·L_a^align + λm·L_m^align + L0`，`L0` = ℓ1 重建 + LPIPS + GAN + VQ loss（following LARP）
- **λa = 1.0，λm = 0.5**（`dera.txt:314-315`）；Table 4 扫了 (0.5,0.5)/(1,0.5)/(0.5,1)/(1,1)，并测了 two-stage（先只对齐图像 20 epoch，再两路 55 epoch，`dera.txt:428-437`）
- Table 2/3：单独对齐任一路都有效，两路同时最好；DINOv3 > DINOv2-B/14 > VideoMAEv2 > InternVideo2-B/14（`dera.txt:341-356`）
- ⚠️ **λ 是在 SACP 之前还是之后施加，论文未说明**（Eq 5 与 Eq 6 的先后关系未交代）。

---

## 3. SACP（Symmetric Alignment-Conflict Projection）

**伪代码**（`dera.txt:187-208`，Algorithm 1；正文解释 `dera.txt:207-236`）

```
输入: encoder 参数 θE, 对齐损失 La_align, Lm_align, 稳定常数 εstab
输出: 重写后的损失 La_re, Lm_re
ga ← ∇θE La_align ;  gm ← ∇θE Lm_align
s  ← <ga, gm>
if s < 0 then
    ca ← stopgrad( s / (‖gm‖² + εstab) )
    cm ← stopgrad( s / (‖ga‖² + εstab) )
    La_re ← La_align − ca · Lm_align
    Lm_re ← Lm_align − cm · La_align
else
    La_re ← La_align ; Lm_re ← Lm_align
end if
```

**实现要点（论文明确给出的）**
- 冲突判定 = 两个损失的 encoder 梯度**内积 s < 0**（`dera.txt:213-215`）
- 投影系数 = 内积除以**对方梯度的 ℓ2 范数平方**（对称，双向投影，故称 symmetric）（`dera.txt:215-219`）
- 系数用 `stopgrad(·)` **detach 成一阶常数**（引 [47] SimSiam），不做二阶（`dera.txt:219-226`）
- 只对 **encoder 参数 θE** 做冲突消解（Algorithm 1 的输入输出签名，`dera.txt:188-191`）；`εstab = 1e-8` 经验取值（`dera.txt:240`）
- 好处：无新增可调超参、开销可忽略（`dera.txt:404-406`）；对比基线是 "Soft Loss"（负内积惩罚项），对权重 0.5/1.0 敏感（Table 5，`dera.txt:398-403`）

**论文未说明的实现细节**（复现缺口）
- 用几次 backward / 是否 `torch.autograd.grad(retain_graph=True)`（论文只说 "negligible overhead"）
- SACP 结果如何与 `L0`（重建/GAN/LPIPS）以及 λa/λm 合并成最终 loss
- 是否每步都算、是否与 AMP/GradScaler/DDP 有特殊处理

---

## 4. LARP 的 1D tokenizer 基座

**结构（论文）** —— `larp.txt:314-350`（§3.2）
- patchify（ViT 式，`fT=4, fH=8, fW=8`，16×128×128 → 1024 patches，`larp.txt:464-469`）
- **Query-based Transformer**：`n` 个可学习 holistic query `QL` 与 patch embedding `E` **沿 token 维拼接**，整体送入 encoder，**只量化 query 位输出**：`Z = E(QL ∥ E), x = Q(Z_{1:n,:})` —— Eq (4)，`larp.txt:319-329`；作者称之为 **in-context conditioning**（`larp.txt:319`）
- decoder 同样是 transformer encoder：`V̂ = reshape(D(QP ∥ Ẑ)_{1:m,:})` —— Eq (5)，`larp.txt:330-348`

**结构（代码，关键文件）**
| 组件 | 文件:行 |
|---|---|
| tokenizer 主类（拼装 encoder/bottleneck/decoder/prior，encode/decode） | `models/larp_tokenizer.py:42-214, 393-469` |
| **encoder/decoder 本体 = `TransformerEncoderParallel`**：`h = cat([context, query]); for block in blocks: h = block(h); return h[:, -query_length:]` | `models/transformer.py:34-69`（核心在 62-69） |
| patchify：`PatchEmbed3D`（t=4）与 `VideoPatchEmbed`（t=1 时用 2D patch embed，按帧拆 batch） | `models/embed.py:16-116`；选择逻辑 `models/larp_tokenizer.py:102-109` |
| bottleneck + **SVQ** | `models/bottleneck.py:65-188`（Bottleneck：in_linear→bottleneck_dim→VQ→out_linear）、`203-324`（SimpleVectorQuantizer） |
| 训练配置 | `cfgs/larp_tokenizer.yaml` |
| trainer（loss 拼装/优化器/DDP/EMA） | `trainers/larp_tokenizer_trainer.py:232-385`，基类 `trainers/base_trainer.py` |

**token 数 / 量化方式**
- `bottleneck_token_num = 1024`（默认值 `models/larp_tokenizer.py:49`；配置 `cfgs/larp_tokenizer.yaml:72`）
- 量化 = **SVQ（随机向量量化）**：codebook 8192、cosine 相似度→softmax→多项式采样、straight-through、（论文 Eq 6-7，`larp.txt:352-378`）
- 代码细节：`l2_normalized=true`、`stochastic=true`、`stochastic_temperature=0.03`、`commitment_loss_weight=0.25`、`codebook_loss_weight=1.0`（`cfgs/larp_tokenizer.yaml:44-54`；实现 `models/bottleneck.py:262-324`，采样在 272-290，STE 在 307）
- ⚠️ **论文/代码不一致**：论文说 codebook 向量维度 `d' = 8`（`larp.txt:498`），但代码把 `bottleneck_dim` 直接作为 codebook 维度（`models/bottleneck.py:130-134`），配置里 `bottleneck_dim: 16`（`cfgs/larp_tokenizer.yaml:42`），且代码注释到处写 `d=16`（如 `models/larp_tokenizer.py:479`）。**仓库版本实际是 16 维**。
- encoder/decoder：hidden 768、heads 12、**depth 12/12**（`cfgs/larp_tokenizer.yaml:80-85`）；decoder 侧 `use_decoder_patch_query_token_type_embed: true`（`:95`）

**关于"bottleneck attention"**
- ❗ 该术语在 LARP 论文与代码里**都不存在**：论文全文 `bottleneck` 只出现一次且指"信息瓶颈"（`larp.txt:524`）；代码里的 `Bottleneck` 是**线性投影 + VQ**，不含 attention（`models/bottleneck.py:65-188`）。真正做信息混合的注意力在 **in-context 拼接的 parallel transformer encoder**（`models/transformer.py:34-69`）。**"bottleneck attention" = 论文/代码未说明**（若你指的是 query 对 patch 的 cross-attention 式压缩，LARP 的实现是 concat + self-attention，而非 cross-attention decoder）。

---

## 5. LARP 仓库可用性

| 项 | 结论 | 出处 |
|---|---|---|
| 许可证 | **MIT**（"Copyright (c) 2024 Hanyu Wang"） | `LICENSE` 第 1-3 行 |
| 依赖 | `requirements.txt`：pandas, einops, easydict, timm, wandb, mergedeep, imageio, transformers, tensorboard, pytorch-msssim, moviepy, decord, lpips；README 要求 torch 2.4.0 / torchvision 0.19.0 / torchaudio 2.4.0 (cu124) | `requirements.txt`；`README.md:24-32` |
| 依赖缺口 | 代码 `from huggingface_hub import PyTorchModelHubMixin`、`import yaml`，但 `huggingface_hub`、`PyYAML` **未列入 requirements.txt**（实测 `grep`）；FVD 需要额外下载 `i3d_torchscript.pt`（dropbox 链接） | `models/larp_tokenizer.py:9`；`train.py:12`；`utils/fvd/fvd.py:328-329` |
| 预训练权重 | HF：`hywang66/LARP-L-long-tokenizer`（173M, rFVD 20）、`hywang66/LARP-L-long-AR`（632M, gFVD 57）、`hywang66/LARP-L-long-AR-FP`（632M, FP FVD 5.1）；代码支持 `from_pretrained` | `README.md:45-50`；`eval/eval_larp_tokenizer.py:34-39` |
| 训练脚本（UCF-101） | tokenizer：`scripts/train_larp_tokenizer.sh`（单卡）/ `_reproduce.sh`（8 卡 DDP），`--csv_file k600_train.csv+ucf101_train.csv`，UCF-101 只作为 val；**AR 生成模型在 UCF-101 上训练**：`scripts/train_larp_ar.sh`（`--csv_file ucf101_train.csv`，`vae.checkpoint hywang66/LARP-L-long-tokenizer`，max_epoch 3000，bs 4）；另有 K600 帧预测脚本 | `scripts/train_larp_tokenizer.sh:4-33`、`scripts/train_larp_tokenizer_reproduce.sh:4-33`、`scripts/train_larp_ar.sh:4-22`、`scripts/train_larp_ar_fp.sh` |
| 数据准备 | `set_datasets.sh` 只需建软链 `data/ucf101`、`data/k600`；**CSV 清单已随仓库分发**：ucf101_train 9538 行 / ucf101_val 3784 / k600_train 426207 / k600_val 29740；格式 `id,path,action,label` | `set_datasets.sh:8-12`；`data/metadata/*.csv` |
| 评测 | `eval/eval_larp_tokenizer.py`（+`eval/rfvd_evaluator.py`）测 rFVD；`sample.py` 采样并算 FVD，可用 10k/50k 样本复现论文数字 | `README.md:87-160`；`eval/eval_larp_tokenizer.py:1-60` |
| **本地副本可直接跑吗** | **不能**。① 无工作区文件（`.git/HEAD → refs/heads/.invalid`，pack 截断）；② `utils/__init__.py:2` 导入 `from .statistics import *`，而 `utils/statistics.py` 缺失 → import 阶段就报错；③ `utils/fvd/i3d_torchscript.pt` 缺失（FVD 评测必需）；④ `third-party/refs/repos/internvideo`、`adaptok` 也是同样的 `.invalid` + `tmp_pack_*` 断链状态。**结论：要复用必须先重新 clone（或补齐上述文件）** | 实测 |

---

## 6. 复现 DeRA 式显式对齐：从 LARP 仓库能直接复用 / 缺什么

### 可直接复用（几乎零改动）
1. **训练框架**：`train.py`（CLI + cfg 的 `$var$` 替换 + DDP 启动）、`trainers/base_trainer.py`、`trainers/larp_tokenizer_trainer.py`（优化器分组/EMA/checkpoint/wandb/可视化），只需在 `larp_tokenizer_trainer.py:320-354` 那段"loss = loss + loss_q*λ + loss_latent_ce*λ"后面追加对齐项与 SACP。
2. **重建监督 `L0`**：`models/loss.py`（`lpips_disc_loss`：L1 + LPIPS + GAN + lecam，含 transformer 判别器），与 DeRA 的 `L0` 定义一一对应（`dera.txt:248-250`）。
3. **Tokenizer 主体**：`models/larp_tokenizer.py` 的 encode/decode 通路、`models/embed.py`（`PatchEmbed3D` + `VideoPatchEmbed` 两条 patchify 路径已存在）、`models/bottleneck.py` + SVQ 量化器。
   - `y = Quant(Za∥Zm)` 极易落地：把 `encode()` 里 `self.bottleneck(z)` 的输入从单路 `z` 换成 `torch.cat([Za, Zm], dim=1)`（`models/larp_tokenizer.py:393-400`），bottleneck 的 `token_nums` 只用于 norm 类型（默认 `norm='none'`，`cfgs:43`），不受影响。
4. **数据管线**：`datasets/video_dataset.py`（`__getitem__` 返回 `{'gt': (T,H,W,3) uint8, ...}`，`datasets/video_dataset.py:339-351`）；外观路只需在 forward 里取 `data[:, :, 0]`（对照 `models/larp_tokenizer.py:458-462`）。
5. **AR 先验 / AR 生成**：`models/gptc.py`、`models/larp_ar.py`、`ar/generate.py`、`sample.py`、`cfgs/larp_ar*.yaml` —— DeRA 用的是"following LARP 的 343M LLaMA-style 生成器"（`dera.txt:305-306`），这套完全可复用。
6. **指标**：`utils/fvd/`、`utils/fid/`、`eval/rfvd_evaluator.py`、`utils/statistics.py`（需补齐缺失文件）。

### 必须自己写（缺什么）
| # | 缺口 | 具体位置/证据 |
|---|---|---|
| 1 | **双 query 集合 + 双 patchify 入口** | 现在只有一套 query：`self.encoder_latent_query_embed = nn.Parameter(torch.zeros(bottleneck_token_num, d))`，`models/larp_tokenizer.py:139`。需要 `Qa(256)/Qm(768)`、外观路的 2D patch 线性层（DeRA 说 "two linear layers"，`dera.txt:150-152`），以及两次前向共享 encoder（`dera.txt:167`）。 |
| 2 | **encoder 中间层特征导出** | `TransformerEncoderParallel.forward` **只返回最后一层的 query 位输出，patch 位输出被丢弃**（`models/transformer.py:62-69`）→ 无法做 Eq (4) 的 patch 位对齐，也无法做 depth=6/8/10/12 的取层消融（`dera.txt:412`）。需要改造成返回 `(patch_out, query_out)` 的逐层输出（或挂 forward hook）。另外拼接顺序（LARP: `[patch, query]`；DeRA 式 (1): `Q∥E`）需选定。 |
| 3 | **图像/视频基础模型的冻结特征抽取** | 本地 `third-party/refs/repos/dinov3/` 有完整官方代码（`hubconf.py`、`dinov3/hub/backbones.py`、configs，含 ViT-B/16），**但无权重**，且许可证是自定义 **DINOv3 License**（非 Apache，需确认商用/分发条款，`LICENSE.md:1-5`）；`internvideo` 本地 clone 断裂，需重拉 + 下载 InternVideo2-B/14 权重。另外还需写：输入分辨率/normalize、**如何把 FM token 数对齐到 Ls=256 / Lt=1024**（DeRA 未说明，见第 2 节）。建议默认：DINOv3 输入 256×256（patch16 → 16×16=256）对齐首帧 256 个 patch；InternVideo2 需使其时间下采样=4（16 帧→4）且空间 16×16，才得 1024（**这是我们的假设，DeRA 未说明**）。 |
| 4 | **两个 MLP 投影头 `h_φ`** | 论文只给了"two-layer MLP"（`dera.txt:220`），隐层维度/共享与否未知 → 需自定并做消融。 |
| 5 | **对齐损失函数** | 负余弦相似度（Eq 4）；LARP 仓库中**完全没有**任何 foundation-model 对齐/REPA 代码（`grep -ri "dino|repa|align|foundation"` 全仓库仅命中注释里的 "FoundationVision" 与 FVD 的 align_corners，`ar/generate.py:2`、`utils/fvd/fvd.py:237`）→ LARP 的"对齐"是**隐式**的（AR prior NLL，`larp.txt:381-404`）。这正好构成 DeRA(显式双专家对齐) vs LARP(隐式 AR 先验对齐) 的对照。 |
| 6 | **SACP 模块 + trainer 集成** | 无任何现成代码（本地无 DeRA 仓库）。需要 `torch.autograd.grad(loss_a, encoder_params, retain_graph=True)` 拿 ga、gm，按 Algorithm 1 重加权后再 backward；与现有 AMP/GradScaler（`trainers/larp_tokenizer_trainer.py:364-374` 用 `self.scaler[0].scale(loss).backward()`）和 DDP 的交互论文未给，需要我们自己设计（建议：对齐损失用 fp32 + 单独 backward，或直接在模型 forward 内构造 reweighted loss 让 scaler 统一处理）。 |

### 对我们的猫身份-动作解耦项目的额外提示
- DeRA 的 **token swapping 实验**（`dera.txt:437-448`，Fig. 7）是"外观/动作 token 可独立可控"的直接定性证据，可作为我们解耦目标的对标可视化；但它的 appearance 语义 = **首帧静态内容**（含身份+背景+姿态），除 DINOv3 监督外**没有身份级监督**，也没有任何身份一致性指标（论文只报 rFVD/gFVD/PSNR/LPIPS，`dera.txt:341-356`）→ 我们的猫身份一致性需要自建指标（ReID/VLM），这是 DeRA 空出的位置。
- 复现成本评估：LARP 基座 + 训练脚本可用（MIT、权重齐全、脚本齐全），**真正的工作量在"双流改造 + FM 特征对齐 + SACP"这三块**，且 DeRA 论文对 MLP 结构 / FM 取层 / token 数匹配 / λ 与 SACP 的先后 **均未说明**，需要我们在 OpenSpec 里把这些当作显式设计决策 + 消融计划写清。

---