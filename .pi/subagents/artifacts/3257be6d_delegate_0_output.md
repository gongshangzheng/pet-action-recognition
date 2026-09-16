# 身份-动作解耦 Tokenizer · FLOAT/LIA 正交运动基 代码+论文精读简报

**范围**：只读。未修改任何文件（`git diff --cached` 为空）。所有引用格式为 `文件:行号` 或 `txt:行号`。

材料路径约定：
- `FLOAT代码` = `third-party/refs/repos/float/`
- `LIA代码` = `third-party/refs/repos/lia/`
- `FLOAT论文` = `third-party/refs/txt/2412.01064_float.txt`
- `LIA论文` = `third-party/refs/txt/2203.09043_lia.txt`

---

## 结论速览

| # | 问题 | 一句话结论 |
|---|------|-----------|
| 1 | 正交基实现 | **既不是 `parametrizations.orthogonal`，也不是手写 Gram-Schmidt**；是 `nn.Parameter(512, M)` + 每次 forward 调 **QR 分解**（`torch.qr` / `torch.linalg.qr`）。论文说的 "Gram-Schmidt" 与代码不一致。 |
| 2 | 潜空间分解 | 身份分量 = 外观编码器输出 `h` 本身；运动分量 = 同一个 `h` 过一个 **5 层 MLP** 得到 λ，再线性组合正交基。加法在 **decoder 输入端**做。 |
| 3 | λ 提取 | 训练/推理时 λ 是 **MLP 预测**出来的，不是内积提取。闭式内积（FLOAT 论文 Eq.15）**只存在于论文，仓库无任何代码**。d=512，M=20。 |
| 4 | FLOAT 改动 | AE 分辨率 256→512；`torch.qr`→`torch.linalg.qr`；decoder 额外吐出 flow；**新增整个生成阶段**（音频/情绪条件 + OT Flow-Matching Transformer）。损失清单见 §4。 |
| 5 | 光流依赖 | **不依赖外部光流估计，也无光流监督**；但 decoder **内部**必用"学习出的稠密 flow + mask + `grid_sample` warp"。基模块本身 warp-free 可直接借用，warp 版 decoder 不可移植。 |
| 6 | 可运行性 | 两者都**不能 pip 安装**；FLOAT 权重可达但**训练代码不发布**；LIA 缺 `augmentations.py`。许可证均为 CC BY-NC（FLOAT README 声称 BY-NC-**ND**，与其 LICENSE.md 自相矛盾）。 |

---

## 1. 正交运动基的实现（代码级）

### 1.1 论文声称
- LIA论文 §3.1，`2203.09043_lia.txt:258-259`：
  > "We implement D_m as a learnable matrix and **apply the Gram-Schmidt process during each forward pass**, in order to meet the requirement of orthogonality."
- 约束式 Eq.(3)，`2203.09043_lia.txt:253-256`：`<d_i,d_j> = 0 (i≠j), 1 (i=j)`。

### 1.2 代码实际（LIA）
`LIA代码/networks/styledecoder.py:439-458`

```python
439  class Direction(nn.Module):
440      def __init__(self, motion_dim):
443          self.weight = nn.Parameter(torch.randn(512, motion_dim))   # 可学习矩阵 D_m_raw
445      def forward(self, input):
448          weight = self.weight + 1e-8
449          Q, R = torch.qr(weight)        # <-- 正交化在这里，每次 forward 都调用
451          if input is None: return Q
454          input_diag = torch.diag_embed(input)      # λ -> diag(λ)
455          out = torch.matmul(input_diag, Q.T)
456          out = torch.sum(out, dim=1)               # out = Σ_m λ_m · Q[:, m]
458          return out
```

### 1.3 代码实际（FLOAT）
`FLOAT代码/models/float/styledecoder.py:418-434`，逐行等价，唯一差别：
```python
422      self.weight = nn.Parameter(torch.randn(512, motion_dim))
426      Q, R = torch.linalg.qr(weight)   # LIA 用 torch.qr
```

### 1.4 实现细节判定
| 问题 | 结论 | 依据 |
|---|---|---|
| `torch.nn.utils.parametrizations.orthogonal`？ | **否**。全仓库 grep `orthogonal\|GramSchmidt\|parametrizations` 在 `.py` 中命中数为 0（仅 FLOAT 注释字符串）。 | `repos/` 内 grep 结果 |
| 手写 Gram-Schmidt 循环？ | **否**。是 `torch.qr`（LAPACK Householder QR），`torch.linalg.qr` 默认 `mode='reduced'`，`torch.qr` 默认 `some=True` → Q 形状 `512×M`，列单位正交。 | `styledecoder.py:449` / `:426` |
| 每次 forward 调用？ | **是**。`Direction.forward` 内部计算，没有缓存、没有 buffer 存 Q；训练与推理都重算。 | `styledecoder.py:445-458` |
| 可学习对象是什么？ | 可学的是**未约束的 `weight` (512×M)**；真正的基 `D_m = Q(weight)` 是它的 QR 像。梯度可以穿过 QR 回传到 `weight`。 | `:443`, `:449` |
| `+1e-8` 作用 | 给全矩阵每个元素加常数，避免整列近零导致 Q 方向不稳（论文未说明，代码意图推断）。 | `:448` |
| 论文 vs 代码不一致 | 论文说 "Gram-Schmidt"，代码用 QR。QR 是正交化但不是经典/修正 Gram-Schmidt 算法。**论文未说明这一差异**。 | 对比 `LIA论文:258` 与 `styledecoder.py:449` |

> ⚠ 可移植性风险（我的分析，非论文原文）：QR 的**列符号/相位不唯一**，且每次 forward 重算 ⇒ 训练后 Q 可能在不同 step/checkpoint 间"旋转"。若要把基当作**稳定 tokenizer 基**使用，建议训练后固化 Q（或改用带缓存的参数化），否则 λ 的语义会漂移。

---

## 2. 潜空间分解 w_S = w_{S→r} + w_{r→S} 的代码落地

### 2.1 论文
- FLOAT论文 Eq.(8)+(9)，`2412.01064_float.txt:235-248`：
  ```
  w_S := w_{S→r} + w_{r→S}                                        (8)
  w_{r→S} = Σ_{m=1}^{M} λ_m(S) · v_m  ∈ R^d                       (9)
  ```
  `w_{S→r}` = identity latent；`λ(S)` = source-dependent motion coefficients；`V = {v_m}` = source-agnostic 正交基。
- 相对迁移形式（LIA Eq.12），`2203.09043_lia.txt:338-340`：`z_{s→t} = z_{s→s} + (w_{r→t} − w_{r→1})`。

### 2.2 两个分量分别由什么产生

**身份分量 `w_{S→r}` = 编码器输出的 512 维 feature 本身（无额外模块）**
- `LIA代码/networks/encoder.py:211-247` `EncoderApp`（StyleGAN2 风格 Conv/ResBlock 下采样塔 + `EqualConv2d(in_channel, 512, 4)`），`forward` 返回 `res[-1].squeeze(-1).squeeze(-1)` = `h`（`:236`）。
- `LIA代码/networks/encoder.py:277-282`：`h_source, feats = self.net_app(input_source)` → 直接作为 `wa` 返回。**没有线性层**。
- FLOAT 完全一致：`FLOAT代码/models/float/encoder.py:198-236`（与 LIA 逐行 diff 仅差 import 顺序/缩进/注释，见下方 diff 证据）。

**运动系数 λ = 5 层 MLP(同一个 h)**
- `LIA代码/networks/encoder.py:254-265`：
  ```python
  255  fc = [EqualLinear(dim, dim)]
  256-257  for i in range(3): fc.append(EqualLinear(dim, dim))
  258  fc.append(EqualLinear(dim, dim_motion))
  259  self.fc = nn.Sequential(*fc)
  ```
  → `EqualLinear(512,512)` ×4 + `EqualLinear(512, 20)`；绑定在 `Encoder.fc`（`dim_motion=20`）。
- `encoder.py:262-265` `enc_motion`：`h, _ = self.net_app(x); h_motion = self.fc(h)`。
- 与论文一致：`LIA论文:259-260` "A_{r→d} is obtained by mapping z_{d→r} ... through a 5-layer MLP"；`LIA论文:761-762` "We use a 5-layer MLP to predict a magnitude vector A_{d→r}"。

**运动分量 `w_{r→S}` = 正交基线性组合（固定线性映射，非学习模块）**
- `styledecoder.py:445-458`：`out = Σ_m λ_m · Q[:, m] = Q @ λ`。一旦 Q 由 `weight` 的 QR 决定，这步就是**纯线性**。

**加法发生在 decoder 输入端（没有独立的"分解模块"）**
- LIA（有驱动帧，3 元组）：`styledecoder.py:520-524`
  ```python
  521  directions_target = self.direction(alpha[0])
  522  directions_source = self.direction(alpha[1])
  523  directions_start  = self.direction(alpha[2])
  524  latent = wa + (directions_target - directions_start) + directions_source
  ```
  这正是 LIA Eq.(12) `z_{s→s} + (w_{r→t} − w_{r→1})` 的代码形式。
- LIA（绝对迁移，1 元组）：`:525-527` `latent = wa + directions`（= Eq.(11) `z_{s→t}=z_{s→r}+w_{r→t}`）。
- 调用点：`lia/evaluation.py:116` `self.gen(img_source, img_target)` 不传 h_start ⇒ `encoder.py:276-278` 走 `h_motion=[h_motion_target]`（长度 1）⇒ 绝对迁移。

**FLOAT 的关键不同：λ 根本进 decoder**
- `FLOAT代码/models/float/FLOAT.py:45-64`：
  ```python
  47   x_r_lambda = self.motion_autoencoder.enc.fc(x_r)     # λ
  48   return x_r, x_r_lambda, x_r_feats
  51   def encode_identity_into_motion(self, x_r):
  52       x_r_lambda = self.motion_autoencoder.enc.fc(x_r)
  53       r_x = self.motion_autoencoder.dec.direction(x_r_lambda)   # w_{r→S}
  56   def decode_latent_into_image(self, s_r, s_r_feats, r_d):
  59           s_r_d_t = s_r + r_d[:, t]      # <-- 加法在这里：w_S = w_{S→r} + w_{r→D̂}
  60           img_t, _ = self.motion_autoencoder.dec(s_r_d_t, alpha = None, feats = s_r_feats)
  ```
- 也就是说 FLOAT 里 `Direction` 的作用**降级为"把源图转成它自己的参考运动向量 w_{r→S}"**（作为 FMT 的条件），而生成的运动 `w_{r→D̂}` 由 FMT 直接在 512 维空间回归得到，**不再经过 λ**。decoder 收到 `alpha=None` ⇒ `styledecoder.py:499-500` `latent = wa`。
- FMT 里 `wr` 的语义有明确 docstring：`FLOAT代码/models/float/FMT.py:205` "`wr: (B, 512) / tensor of reference motion latent (i.e., r -> s)`"。
- 与论文一致：`2412.01064_float.txt:205-211`（Fig.2 caption）"Given ... the reference motion `w_{r→s} ∈ R^d` ... the sequence of latents `w_{S→D̂^1:L} := (w_{S→r} + w_{r→D̂^l})` are decoded into the video"。

### 2.3 代码级证据：FLOAT 的 encoder/styledecoder 是 LIA 的派生
`diff` 结果（去缩进后）：`lia/networks/encoder.py` 与 `float/models/float/encoder.py` 差异**仅为** 版权头、import 顺序、注释删除、`FusedLeakyReLU` 类位置移动 —— **网络结构逐层相同**。`styledecoder.py` 差异为：`torch.qr→torch.linalg.qr`、`ToFlow` 多返回 `flow`、加了一个 `out.size(2)==64` 分支、`Synthesis.forward` 返回 tuple、`make_kernel` 位置移动。这与 FLOAT论文 `:1227` Fig.17 caption "The notations are adopted from LIA [85] and StyleGAN2 [33]" 吻合。

---

## 3. 运动系数 λ 的提取方式 / d 与 M 的数值 / 参数名

### 3.1 λ 的来源：**预测**，不是内积提取
| 场景 | λ 来源 | 证据 |
|---|---|---|
| LIA 训练准备（论文） | 5 层 MLP 映射 encoder 输出 | `LIA论文:259-260`, `:761-762`；代码 `encoder.py:262-265` |
| LIA 推理（驱动帧） | 每帧驱动图过 encoder → `fc` | `LIA代码/evaluation.py:114-116`, `encoder.py:274` |
| FLOAT 推理（源图参考运动） | `fc(s_r)` → `direction` | `FLOAT.py:47,52-53,163` |
| FLOAT 生成运动 `w_{r→D̂}` | **FMT 直接回归 512 维向量**，不经 λ | `FLOAT.py:56-64`, `FMT.py:250-262` |

### 3.2 闭式内积：只在论文，仓库无实现
- 论文 Eq.(15)，`2412.01064_float.txt:444`（§5.4 Test-time Pose Editing）：
  ```
  <w_{r→D̂}, v_k> = <Σ_m λ_m(D̂)·v_m, v_k> = λ_k(D̂)      (15)
  ```
  正文 `:438-446`："We can always compute these coefficients **in closed form by taking inner products** ... We refer to this test-time editing technique as **λ-control**."
- **代码验证**：`grep -rni "lambda|inner product|editing|einsum" float --include=*.py` 只命中 `FMT.py:155`(Python lambda) 与 `FLOAT.py:47,52,159,163`(变量名 `x_r_lambda`) —— **无任何内积/编辑代码**。FLOAT README `:155` 明确 "This repository includes only the inference code; the training code will not be released."
- LIA 的"编辑"是直接**写 α 输入**，不是内积反解：`LIA代码/linear_manipulation.py:74-95`
  ```python
  83  alpha = torch.zeros(1, args.latent_dim_motion).cuda()
  89-90  alpha[:, i] = 1.0 * delta          # delta ∈ [-3, 3]，range=16 步
  92  img_recon = self.gen.synthesis(wa, [h_start, alpha, alpha_zero], feat)
  ```
  CLI 默认 `--degree 3.0 --range 16`（`:82-83`）。

### 3.3 数值
| 量 | 值 | 论文出处 | 代码出处 |
|---|---|---|---|
| 潜空间维 `d` (N) | **512** | `LIA论文:364` "The dimension of all latent codes, as well as directions in D_m is set to be 512"；`FLOAT论文:434` "The motion latent dimension is set to be `d = 512`" | **硬编码** `nn.Parameter(torch.randn(512, motion_dim))`（`styledecoder.py:443` / `:422`）；FLOAT 另设 `--dim_w 512`（`FLOAT代码/options/base_options.py:39`，`--style_dim 512` 在 `:37`） |
| 基个数 `M` | **20** | `FLOAT论文:434-435` "with `M = 20` distinct orthogonal directions"；`LIA论文:465,481` Tab.5 消融 M∈{5,10,20,40,100}，**20 最优** | FLOAT `--dim_m 20`（`base_options.py:41`，help 文本 "dimension of orthogonal basis"）；LIA `--latent_dim_motion 20`（`linear_manipulation.py:87`, `run_demo.py:114`, `predict.py:28`, `evaluation.py:138`） |
| 编码器输出维 | 512 | `LIA论文:364` | `EncoderApp` 最后 `EqualConv2d(in_channel, self.w_dim=512, 4)`（`encoder.py:247`） |
| 隐层/注意力（FLOAT FMT） | h=1024, heads=8, T=2, L=50, L'=10, NFE=10 | `FLOAT论文:435-440, 403-405` | `base_options.py:45-47,49,54` |

**代码参数名清单**
- 基矩阵：`Synthesis.direction.weight`（`Direction.weight`），形状 `(512, 20)`
- λ 预测器：`Encoder.fc`（`nn.Sequential(EqualLinear×5)`）
- FLOAT opt：`--dim_w`(512), `--dim_m`(20), `--style_dim`(512), `--dim_a`(512), `--dim_h`(1024)
- LIA CLI：`--latent_dim_style`(512), `--latent_dim_motion`(20)

---

## 4. FLOAT 相对 LIA 改了什么 + FLOAT 完整训练目标

### 4.1 除面部组件损失以外的改动

| # | 改动 | 证据 |
|---|---|---|
| 1 | **AE 输入分辨率 256 → 512** | FLOAT论文 `:419` "resize the facial region to 512² resolution"；Fig.17 `:1199-1213` 首层 feature map 为 512×512；代码 `--input_size 512`（`base_options.py:16`）。LIA 为 256（`LIA论文:358,786`；`--size 256`） |
| 2 | **`torch.qr` → `torch.linalg.qr`** | `LIA stylededecoder.py:449` vs `FLOAT styledecoder.py:426` |
| 3 | **decoder 额外返回 flow field** | `FLOAT styledecoder.py:415` `return feat_warp, feat_warp+..., out, flow`；`:526` `return img, flow`；`generator.py:20-22` `return {'d_hat': ..., 'flow': ...}`。LIA 返回 3 值（`:436`）。**论文未说明该 flow 输出用途（AE 目标 Eq.18 中无 flow loss）** |
| 4 | **新增整个生成阶段**：OT-based Flow Matching Transformer (FMT) 在 512 维运动潜空间采样 | FLOAT论文 §4.2 `:239-311`；代码 `models/float/FMT.py`（frame-wise AdaLN + masked self-attention，`FMT.py:166-262`）。LIA **没有**任何生成模型，运动来自驱动帧 |
| 5 | **新增条件编码器**：wav2vec2 音频编码器 + 语音情绪识别器；CFV 语音/情绪双引导 | FLOAT论文 `:312-338`；代码 `FLOAT.py:184-251`（`AudioEncoder`/`Audio2Emotion`），`FMT.py:264-282`（`forward_with_cfv`） |
| 6 | **训练数据换为 HDTF+RAVDESS+VFHQ**（LIA: VoxCeleb/TaichiHD/TED） | FLOAT论文 `:402, 918-923`；LIA论文 `:357` |
| 7 | 其它 | LIA `Synthesis.forward` 用 `wa.size(0)`（`:516`，未使用）；FLOAT 加 `out.size(2)==64` 分支用于取 flow（`:516-518`） |

### 4.2 FLOAT 运动潜空间自编码器（motion latent AE）训练目标 —— 完整清单与权重

论文 §A.3 Eq.(18)，`2412.01064_float.txt:910-924`：

```
L_total = L_L1
        + λ_lp        * L_lp
        + λ_comp-lp   * L_comp-lp
        + λ_full-adv  * L_full-adv
        + λ_eye-adv   * L_eye-adv   + λ_eye-FSM * L_eye-FSM
        + λ_lip-adv   * L_lip-adv   + λ_lip-FSM * L_lip-FSM          (18)
```

**权重值**（§A.4，`2412.01064_float.txt:911-915`）：

| 系数 | 值 |
|---|---|
| λ_lp | **10** |
| λ_comp-lp | **100** |
| λ_full-adv | 1 |
| λ_eye-adv | 1 |
| λ_eye-FSM | **100** |
| λ_lip-adv | 1 |
| λ_lip-FSM | **100** |
| L1 | 系数 1（隐含） |

**各项定义**
- `L_lp`：VGG-19 多尺度感知损失（`:920-921` "Ll_p is the VGG-19 [66] based multi-scale perceptual loss [95] similar to Lcomp-lp"）。
- `L_comp-lp`：Eq.(17)，`:854`：
  ```
  Σ_{i=1}^{N} (1/|M_i|) ‖ M_i ⊙ φ_i(D̂) − M_i ⊙ φ_i(D) ‖_1
  ```
  N=4 层 VGG-19 金字塔；`M_i` 为面部部件二值 mask（**在 feature 上做 mask，不只是图像**，`:866`）；mask 由 off-the-shelf 人脸分割模型（嘴部窄区域）+ 人脸关键点检测器（眼部 bbox）产生（`:868-872`）。
- `L_full-adv`：非饱和对抗损失，2-scale discriminator（取自 StyleGAN2 [33]），Eq.(19)，`:924`：`−log[Disc_full(D̂)]`。
- `L_{x-adv}` / `L_{x-FSM}`：Eq.(21)，`:931`：
  ```
  L_{x-adv} = −log[Disc_x(D̂_x)]
  L_{x-FSM} = ‖ Gram(ψ(D_x)) − Gram(ψ(D̂_x)) ‖_1        x ∈ {eye, lip}
  ```
  `ψ` = 部件判别器学的多分辨率特征，`Gram` = Gram 矩阵（`:937-939`）。
- **AE 训练设置**：Adam，batch 8，lr 2e-4，460k steps，单卡 A100 ≈9 天（`:914-917`）。

**运动采样阶段（FMT）目标**（§4.2，`:299` Eq.11、`:314` Eq.12、`:324` Eq.13）：
```
L_OT(θ)  = ‖ v_t^{1:L}(x_t,c_t;θ) − u_t(x|w_{r→D^{1:L}}) ‖ + ‖ v_t^{−L':0}(...) − w_{r→D^{−L':0}} ‖   (11)
L_vel(θ) = ‖ Δv_t − Δu_t ‖                                                                          (12)
L_total(θ) = λ_OT L_OT + λ_vel L_vel,   λ_OT = λ_vel = 1                                            (13)
```
- 目标向量场 `u_t(x|w_{r→D^{1:L}}) = w_{r→D^{1:L}} − x_0`，`φ_t(x_0)=(1−t)x_0 + t w_{r→D^{1:L}}`（`:290-292`）；`‖·‖` 用 **L1**（`:442-443`）；Euler 求解器、NFE=10（`:446, 403-405`）；Adam lr 1e-5、batch 8、2,000k steps ≈2 天（`:441-445`）。
- 注：LIA 的自编码器损失为 `L_recon(L1) + λL_vgg + L_adv`，λ=10（`LIA论文:295-322, 364-365`）。FLOAT 在其上加了 comp-lp 与三个部件判别器族。

---

## 5. 是否依赖光流？移植到视频 tokenizer 的取舍

### 5.1 依赖判定：**不依赖外部光流，但内部必然用学习出的 flow + warp**

| 判断 | 证据 |
|---|---|
| **无外部光流估计网络 / 无光流监督** | LIA论文 `:166-167` "self-supervised manner, only relying on RGB videos for both, training and testing **without any priors**"；`:82-83` "fully **eliminate the need of explicit structure representations**"；`:189-191` 训练目标只有 "reconstruct x_d"；Eq.(7)(8)(9) `:297-320` 只有 L1 + VGG + adv，**无 flow loss**。FLOAT AE 目标 Eq.(18) 同样无 flow 项。 |
| **decoder 内部必用稠密 flow field + mask + `grid_sample`** | LIA `styledecoder.py:405-436` `class ToFlow`：`sampler=tanh(out[:,0:2])`（`:430`）、`mask=sigmoid(out[:,2:3])`（`:431`）、`flow = sampler + identity_grid`（`:432`）、`feat_warp = F.grid_sample(feat, flow) * mask`（`:434`）。FLOAT 完全同构：`styledecoder.py:385-415`（`:413` grid_sample）。 |
| **多尺度 flow 金字塔** | LIA论文 `:272-290` "pyramid of flow fields φ_{s→d}={φ_i}"、"multi-scale masks {m_i}"；代码 `Synthesis.forward` 每尺度调 `to_flow`（`styledecoder.py:538-547`；FLOAT `:509-522`） |
| **论文自述仍需 warp** | LIA论文 `:216-217` "G decodes it as a dense flow field φ_{s→d} ... and uses φ_{s→d} to **warp** x_s"；`:269` "we use G to decode a flow field φ_{s→d} and warp x_s" |
| FLOAT 的 AE 结构图也画了 warp | FLOAT论文 Fig.17(d) `:1210-1212` 出现 `ToMask` / `ToFlow` / **`Warp`** 三个模块 |

> 一句话：**光流不是输入/监督，而是 decoder 的输出手段**。去掉 warp 就等于去掉 decoder 的一半。

### 5.2 可移植到"视频 tokenizer 动作 latent"的部分

**A. 可直接借用（warp-free，总计 ~30 行）**
1. `Direction` 模块整体（`LIA styledecoder.py:439-458` / `FLOAT :418-434`）：`nn.Parameter(dim, M)` + QR + `Σ_m λ_m q_m`。只需把硬编码 `512` 换成你的动作 latent 维度。
2. 加法式组合 `w = w_identity + Σ λ_m v_m`（`Synthesis.forward:524-527` / `FLOAT.py:59`）以及**相对迁移形式** `w_{r→s} + (w_{r→t} − w_{r→1})`（LIA Eq.12 / `styledecoder.py:524`）。
3. 闭式 λ 读出（论文 Eq.15）：一旦基正交，编辑/clamp 单个 λ 不会串扰——这是"动作 token 可解释、可解耦"的直接可复用性质。
4. 正交性作为**解耦先验**：λ_i 对第 i 个方向的贡献与其它方向内积为 0（Eq.3 / Eq.15），适合作为动作 token 的独立通道。

**B. 必须改（或不可移植）**
1. **512 维潜空间不是视频 tokenizer latent**：它是 StyleGAN2 风格的 appearance/W+ 潜在码 + 对抗重建学出来的。基的"运动语义"完全来自 **warp 版 decoder 的重建损失**。如果去掉 warp，就**没有任何项在驱赶基指向"运动"** ⇒ 必须自备目标函数（例如：动作 latent 的时序速度损失，可参考 FLOAT `L_vel` Eq.12；或跨身份重建/一致性）。**论文未讨论此迁移，属推断。**
2. **warp 版 decoder 全链不可移植**：`latent → ToFlow(3ch:2 flow+1 mask) → grid_sample(feat)`（LIA `:542-547`，FLOAT `:508-522`）正是"不用 warp"时必须重写的部分。`ModulatedConv2d`（StyleGAN2 调制卷积）、`ConstantInput`、`ToRGB` 也都绑定在图像合成上。
3. **λ 预测器形态不匹配**：5 层 `EqualLinear` 作用在**全局池化后的单帧 512 维特征**上（`encoder.py:262-265`）——无时序、无 patch 结构。视频 tokenizer 需要换成 tube/patch 级时序编码器输出。
4. **加法可组合性不被保证**：LIA 的分解隐含"存在一张 canonical pose 参考图 x_r 且 flow 能表达全部运动"（论文 `:485-489` 显示 x_r 是一致的正面 canonical pose）。没有 warp 时，latent 空间未必线性可加 ⇒ 身份/动作解耦需重新验证。
5. **秩只有 20**：M=20 个方向只张成 512 维中的 20 维子空间（`styledecoder.py:443`）。若身份信息落在这 20 维内，λ 就会携带身份 ⇒ 正是本项目要避免的泄漏。建议：显式对 λ 与身份 latent 做正交/互信息约束。**论文无此实验。**
6. **QR 的符号/重算不稳定**（见 §1.4 风险框）：要当 tokenizer 基使用，建议固化 Q 或用稳定参数化。

---

## 6. 依赖与可运行性

| 维度 | LIA (`wyhsirius/LIA`) | FLOAT (`deepbrainai-research/float`) |
|---|---|---|
| 仓库 commit | `b9f15fb70a3b7704576491ef8f4fd6fc4ad557d9` (2025-10-22, "Update README.md") | `3b5b2dfc3e65df26e7fbba17d9adb3f43747851c` (2025-11-10, "update") |
| 依赖声明 | **无 `requirements.txt`**；README `:15-22` 列 Python 3.7 / PyTorch 1.5+ / tensorboard / moviepy / av / tqdm / lpips；`cog.yaml:1-16` pin `torch==1.10.1, torchvision==0.11.2, moviepy==1.0.3, tensorboard==2.9.1, av==9.2.0, python 3.8, cuda 11.0` | **有 `requirements.txt`**：pyyaml, opencv-python, pandas, tqdm, matplotlib, flow-vis, librosa, `transformers==4.30.2`, `albumentations==1.4.15`, `albucore==0.0.16`, `torchdiffeq==0.2.5`, `timm==1.0.9`, `face_alignment==1.4.1`, `av==12.0.0`；`environments.sh` 另 pin `torch==2.0.1 / torchvision==0.15.2 / torchaudio==0.2.0 (cu118)`；README 要求 Python 3.8.5 |
| 可 pip 安装？ | **否**（无 setup.py/pyproject）。只能作为源码运行，且 `from networks.generator import Generator` 要求 CWD = 仓库根 | **否**（无 setup.py/pyproject）。`from models.float.FLOAT import FLOAT`、`from options.base_options import BaseOptions` 同样要求 CWD = 仓库根 |
| 权重可得性 | 仓库内仅占位符 `checkpoints/put checkpoints here`；真实权重在 Google Drive 文件夹（README `:26`，链接 `drive.google.com/drive/folders/1N4QcnqUQwKUZivFV-YeBuPyH4pGJHooc`）。**本地未验证可下载（无网络访问）** | `download_checkpoints.sh` 用 `gdown --id 1rvWuM12cyvNvBQNCLmG4Fr2L1rpjQBF0` → `float.pth`；另需两个 HF 模型放到 `./checkpoints/`：`facebook/wav2vec2-base-960h`、`r-f/wav2vec-english-speech-emotion-recognition`（README `:64-95`）。代码在 `FLOAT.py:186, 209, 234` 用 `from_pretrained(..., local_files_only=True)` ⇒ **必须预先本地下载**。**本地未验证** |
| 训练代码 | **无**（仓库只有 `encoder/generator/styledecoder/utils` + 推理脚本；无 discriminator、无 train loop）⇒ 论文的 L1+VGG+adv 目标无法复现 | **无**。README `:155` "**the training code will not be released**" ⇒ 运动潜空间 AE 的 Eq.(18) 目标**不可复现**，只能加载 `float.pth` 里的预训练基/解码器 |
| 已知运行缺口 | `lia/dataset.py:17` `from augmentations import AugmentationTransform` —— 仓库**不存在** `augmentations.py` ⇒ `dataset.py` / `evaluation.py` 导入即失败；`predict.py:17` 依赖 `cog` 包 | `models/wav2vec2.py` 与 `models/wav2vec2_ser.py` 依赖 `transformers==4.30.2`（严格 pin）；`generate.py:5` 依赖 `face_alignment` 做自动裁脸 |
| 许可证 | CC BY-NC 4.0（`LICENSE.md:1` "Attribution-NonCommercial 4.0 International"；**全文 0 次 `NoDerivatives`**，即允许非商业衍生）。每个源文件头 `:5-6` 注明 "free for non-commercial, research and evaluation use" | **矛盾**：README `:151` 声明 CC BY-NC-**ND** 4.0（NoDerivatives，链接 `creativecommons.org/licenses/by-nc-nd/4.0/`），但仓库 `LICENSE.md:1,13` 文本是 CC BY-NC 4.0（无 ND）。`README:35` 也写 Non-commercial License 指向 by-nc-nd |
| 对我们的风险 | 非商业研究可用；训练代码缺失 ⇒ 想改 AE 目标必须自己实现 | ND 若成立则**不允许衍生**（移植/改写有法律风险），与其 LICENSE.md 冲突 ⇒ **建议只借鉴思路（本文所提取的算法描述），代码自行重写，并请法务/用户确认许可** |

---

## 7. 代码质量/坑点清单（额外发现，供实施时避坑）

1. `FLOAT代码/models/float/styledecoder.py:528-566` `Synthesis.synthesis(self, wa, feats)` 内部引用**未定义的 `alpha`** ⇒ 一旦被调用即 `NameError`。属死代码：`models/float/generator.py:15-17` 的 `Generator.synthesis` 实际调的是 `self.dec(...)` = `Synthesis.forward`，**不是** `Synthesis.synthesis`。**论文未提及。**
2. `FLOAT.py:160-163` `if 's_r' in data: ... else: ...` —— `generate.py:74` 构造的 dict 只有 `{'s','a','p','e'}`，**该分支永不成立**；且两分支计算结果**完全相同**（都是 `fc` + `direction`）。死分支。
3. `r_cfg_scale` 串了整条链路（`base_options.py:62` 默认 1.0、`generate.py:207`、`FLOAT.sample(..., r_cfg_scale)`），但 `FMT.forward_with_cfv`（`FMT.py:264-282`）**只用了 a/e 两个 cfg**，`null_wr` 计算后未使用 ⇒ **参考 CFG 在发布代码中是 no-op**。
4. LIA `styledecoder.py:516` `bs = wa.size(0)` 计算后未使用；`styledecoder.py:424` 把 identity grid 硬编码 `.cuda()`（多卡/CPU 不友好）。FLOAT 已改为 `align_corners=False` 显式（`:413`），LIA 省略该参数（默认 False，行为等价）。
5. FLOAT 的 AE 结构为 512×512 输入（`base_options.py:16`），显存/算力开销显著高于 LIA 的 256×256 —— 若要再训练自己的版本，这是主要成本项。
6. FLOAT 论文 Eq.(16)（`2412.01064_float.txt:861-866`）文本"the identity latent `w_{r→S}` is decoded into image featuring the average head pose"与 Eq.(8) 的记号自相矛盾（按 Eq.(8)/代码，身份 latent 是 `w_{S→r}`，`w_{r→S}` 才是运动分量）。**论文笔误，以代码为准**（`FLOAT.py:56-60`、`FMT.py:205` docstring）。

---

## 8. 对本项目 tokenizer 设计的直接启示

1. **正交基机制本身极轻**：一个 `nn.Parameter(dim, M)` + 每 forward 一次 QR + 一次 `Q @ λ`。移植成本几乎为 0（§5.2-A）。
2. **真正的难点不是基，而是"身份-运动的分解从哪里得到监督"**。LIA/FLOAT 的分解之所以成立，是因为 decoder 要用 `w_{S→r} + w_{r→S}` 通过 **warp 重建驱动帧**（论文 `:190-191`）。一旦禁用 warp（本项目要求），必须显式设计新的解耦监督（推荐组合：动作 latent 的时序速度损失 `L_vel` + 跨身份交换一致性 + λ⊥身份 的正交/HSIC 约束）。
3. **数值先例可直接沿用**：d=512、M=20。若动作 token 维度不同（例如 256/768），M 需要重新按 M≪d 选择（LIA Tab.5 显示 20 是甜点，40/100 不再提升）。
4. **法律面**：FLOAT 的 ND 声明是阻塞项 ⇒ 建议**只借鉴算法（本文提取的公式/机制）**，实现自行编写；LIA 的 CC BY-NC 允许非商业衍生，但仍不能商用。

---

## 不确定 / 论文或代码未说明的点

- FLOAT AE 训练目标 Eq.(18) 中的 `L_lp` 具体实现细节（论文只说"VGG-19 multi-scale perceptual loss similar to Lcomp-lp"，`2412.01064_float.txt:920-921`）——**未给出层选取与归一化细节**。
- `Generator.forward` 返回的 `flow`（`generator.py:20-22`）用途：**论文/代码均未说明**（AE 目标里无 flow 项）。
- 权重文件的实际可下载性、实际大小、`float.pth` 中 `Direction.weight` 的具体数值：**本地无网络，未验证**。
- LIA 官方仓库分辨率 256 与 FLOAT 对 LIA 复现实验标注的 "256×256"（`2412.01064_float.txt:896` 表注）一致，但 FLOAT 自己 AE 用 512 —— 二者不可直接数值对比。
- 相对迁移中 `directions_source`（`styledecoder.py:522`）与 `alpha_zero`（`linear_manipulation.py:89`）的关系：**论文 Eq.(12) 用 `w_{r→s}` 表示源-目标差异运动，代码把 `directions_target - directions_start` 与 `directions_source` 分开相加，论文未逐项对应解释**。代码路径与 Eq.(12) 一致（`h_start=h_motion(frame 0)`，见 `run_demo.py:96`），但 `directions_source` 的语义偏置缺乏论文论证。

---

## 验收报告