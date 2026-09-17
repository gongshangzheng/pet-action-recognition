# TivTok / SIF 备档（已评估，暂不采用）

> **状态：备档（2026-09-17）**
>
> 本文汇总 TivTok 及其 **SIF（Scope-Induced Factorization）** 双 token 机制的全部调研结论。
> **主线架构已改为参考 FLOAT**（身份来自参考输入 + 正交运动基），TivTok 的 SIF **暂不采用**——原因见 §7。
> 保留本文的目的：① 决策可追溯；② 若将来"身份必须从视频内推断"的需求复活，材料现成。
>
> 相关：[`tokenizer-architecture-refs.md`](./tokenizer-architecture-refs.md)（全谱系调研）、[8 号《身份-动作 Tokenizer》](../../management/docs/identity-tokenizer.md)（现主线设计）

## §1 是什么

**TivTok**（arXiv 2606.17590，清华，2026-06）是一个**视频 tokenizer**：用两组互补的 token 表达一段视频。

| 组 | 语义 | 注意力范围 |
|---|---|---|
| **TIV**（Time-Invariant） | 跨帧共享的**时间不变**语义结构（论文示例：可复用于更长视频） | **全部帧** patch + 全部 TIV + 全部 TV |
| **TV**（Time-Variant） | 每帧特有的**时间可变**残差细节 | 第 t 帧 patch + 全部 TIV + 自己 |

**核心思想（SIF）**：论文原话——

> "一个 token 的信息流应当匹配它的表征角色——要捕捉时间不变量的 token 必须看到整个序列；要捕捉帧级残差的 token 必须被阻止吸收跨帧信息。"

**分解由架构诱导，无显式监督。** 论文明确**否定因果掩码**（会让 TV 吸收跨帧信息，与 TIV 职责重叠）。

**解码**：Invariant Broadcasting（IB）——每帧复用同一份 TIV，与该帧 TV 拼接并行重建，解码复杂度从 O(T²) 降到 O(T)。

## §2 关键数值（论文推算，自洽）

| 项 | 值 |
|---|---|
| encoder / decoder | 12 层、hidden 768、patch **4×8×8**、**3D RoPE** |
| 训练分辨率 / 帧数 | 256×256、16 帧 |
| latent 维度 D | T128→128、T512→32、T1024→16 |
| **N_TIV : N_TV** | **≈ 3:1**（T128@16帧 = TIV 96 + TV 2/帧 = 32；T512 = 384+128；T1024 = 768+256）|
| 底座 | **ViT-based SoftVQ-VAE**（arXiv 2412.10958）|

**SIF 消融代价**：去掉 SIF → PSNR 19.67 / rFVD 1359.38（论文 Table 6）。

## §3 训练配方

```
损失：L = L1 + λ1·perceptual + λ2·adversarial      λ1 = 1, λ2 = 0.2
判别器：DINOv2-S，从 30K iter 开始
LeCAM 正则：0.001
优化：AdamW、wd 1e-4、β=(0.9, 0.95)、global batch 64、lr 1e-4
      5K warmup、cosine、100K iter
数据：UCF-101 + K600 混合
```

## §4 实现路径（若将来要用）

**⚠️ TivTok 未开源**（无代码链接、未声明将发布）→ 必须自研。

**SIF 需要自定义 attention mask**，注意两点：
1. **TiTok 官方代码的 attention 不支持任何 mask**（`modeling/modules/blocks.py` L85–131）→ 需参考 `modeling/rar.py` L90–124 的 `attn_mask` 版 SDPA 实现
2. AdapTok（MIT）已带完整 mask 生成框架（`models/mask_generator.py`）与 SDPA mask 通路（`models/block.py:36-61`）→ **实现 SIF 只需新增一个 `attn_type`**，其中：
   - AdapTok 现有 mask 都是**块因果**（只能看同块/前块）
   - SIF 要求 **TIV 看全段（含未来）** → 必须新增**非因果**类型

```
新增 attn_type = "tiv_tv"：
  TIV tokens  → 全部帧 patch + 全部 TIV + 全部 TV    （全局，非因果）
  TV tokens(t) → 第 t 帧 patch + 全部 TIV + 自己       （局部）
```

## §5 论文出处索引

| 主题 | 位置 |
|---|---|
| SIF 定义 | `txt/2606.17590_tivtok.txt` §3.3（L252–300，Eq. 3/4）|
| 分解由架构诱导 | 同上 L291–295 |
| 否定因果掩码 | 同上 L296–299 |
| TIV 语义分析（捕获身份而非像素静止）| 同上 §4.5 |
| 底座声明（SoftVQ-VAE）| 同上 L356 |
| 消融 | 同上 Table 6 |

## §6 曾如何影响我们的设计

在 2026-09-16 的架构收敛中，TivTok 曾是**骨架主源**：

- 双 token 骨架 = TIV（管身份）+ TV（管动作）
- 正交运动基挂在 TV 通道上，得到逐帧 `λ_m(t)`
- `N_TIV : N_TV = 3:1`、patch 4×8×8、12 层/768 维等超参均照此口径
- 我们还据此把 `N_TIV` 从 16 修正为 96（原写法方向反了）

**仍然可迁移的部分**：TivTok 的 **Invariant Broadcasting（每帧复用同一份全局 token）在数学上等价于 FLOAT 的加法广播**（`w_{S→D̂_l} = w_{S→r} + w_{r→D̂_l}`）。所以从 TivTok 迁到 FLOAT，这部分是**平滑过渡**，不是推翻。

## §7 为什么最终没采用（2026-09-17 用户裁定）

**直接原因**：身份提取来源从"视频内推断"改为"**参考输入**"（用户事先拍摄单图/多视角图/短视频）。

**逻辑链**：

```
身份由参考输入提供（FLOAT 式，给定而非推断）
        ↓
视频内的 TIV 与身份通道职责重叠 → 冗余
        ↓
SIF 的存在意义（在同一段视频内分离身份与动作）消失
        ↓
TivTok 骨架不再需要；重心转向 FLOAT
```

**更深层的原因**：SIF 只能给出**软分离**（靠注意力范围诱导），而 FLOAT 给出的是**硬分离**（身份来自独立输入流）+ **完整性保障**（正交基容量闸门：运动压到 M 维 → 外观只能进身份）。

| | TivTok SIF | FLOAT |
|---|---|---|
| 身份来源 | 视频内推断 | **独立参考输入**（给定）|
| 分离强度 | 软（注意力范围诱导）| **硬**（输入流分离）|
| 身份完整性保障 | ❌ 无 | ✅ 正交基容量闸门 + 重建 |
| 所需监督 | 需额外约束（我们曾用 InfoNCE → 已证明不适用）| **无需**（重建即可）|

**保留的备档价值**：若将来出现"用户无法提供参考、必须从视频内推断身份"的场景，SIF 是现成的候选方案，材料见本文 §1–§5。
