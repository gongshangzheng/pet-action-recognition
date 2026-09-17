# Proposal: video-action-segmentation

> ⚠️ **职责修订（2026-09-17 用户裁定）**：本 change **只负责 L5 动作分割（找边界）**，**不贴标签**。
> **L6 动作识别（每段 → 类别）** 由 `video-feature-latent`（行为簇聚类 + 命名）承接；拆开理由见架构 §4.5/§4.6。

> 子 change，总管：`pet-motion-latent-pipeline`（**2.4b 主线**）。**性质：研究型**（2026-09-17 用户裁定正式立项）。

## Why

### 问题：行为素 ≠ 动作

用户提出的类比：

```
行为素 = 单词        动作 = 句子（由多个行为素拼成）
```

`video-feature-latent` 阶段一/二做的「窗口特征 → 聚类 → 行为簇 + 人工命名」建的是**行为素词表（词层）**，**没有到"动作"（句层）**。

**后果**：若就此停下，输出的是「这一瞬间是第 7 号行为素」，而**给不出「猫在舔毛」**（= 7 号词重复 20 次 + 特定节奏）——而后者才是用户要的答案。

### 更严重的：出口形态要求"段 + 时间戳"

```
用户要的答案：「3:00–3:15 舔毛，3:15–3:40 走动，3:40–4:10 睡觉」
                              ↑ 多个变长段 + 时间戳
```

而**主流动作识别模型（A1 层）给不出时间戳**——它输出恒定 1 个标签（详见 [`papers/docs/action-recognition-models.md`](../../../papers/docs/action-recognition-models.md)）。
→ 所以"分段"不是一个可选增强，而是**出口形态的必要前置**。

### 已有成熟子领域可直接借鉴（不必自研）

**无监督时序动作分割（Unsupervised TAS）** 的输入输出与本项目**完全一致**：

```
输入：长视频（未裁剪、含多个动作）
输出：段边界 + 每段一个【学到的】类别
标注：不需要
```

代表工作：TAEC（arXiv 2303.05166）、Temporally-Weighted Hierarchical Clustering（arXiv 2103.11264）、CTE（2019）、ASAL（2023）。
另有音频范式可迁：无监督分词 + 词表发现（arXiv 1603.02845）、层次 HMM + 时长先验（arXiv 1806.01665）、NLP unigram 分词（DP/Viterbi）。

## What Changes

- **新增「行为素 → 动作段」的分割/分词层**（管线新增一环，位于 L4 动作表征之后、出口之前）
- **三步组合**：
  1. **λ 运动能量预分段**（零成本）：`Σ_m|λ_m(j)|` 低能量段作**强边界候选** → 长视频降维成若干「行为块」
  2. **无监督 TAS 细分段 + 类型聚类**（每块内）
  ~~3. 人工命名段类型~~ → **已移出本 change**（归 L6 `video-feature-latent`）
- **输入契约**：消费 ① `λ` 序列（来自 `identity-action-tokenizer`）② 段/窗口表征（来自 `video-feature-latent`）
- **产出**：**只有边界的段列表**（起止时间 + 边界置信度），供 L6 贴标签后交 `spot-check-cli`
- **静态物体**（本 change 不做）：纯静止是否为行为（睡觉 vs 停顿）由**时长阈值**区分

## Capabilities

### New Capabilities
<!-- 无新 capability：属运动管线后段，沿用 motion-pipeline -->

### Modified Capabilities

- `motion-pipeline`: 新增「行为素序列 → **动作段边界**」的分割要求——给定行为素 / `λ` 序列，系统 SHALL 输出**段边界列表**（MUST NOT 贴动作标签），并 MUST 对「静止段」按**时长阈值**区分「停顿（分隔符）」与「静止型行为」

## Impact

- **管线新增两环**：架构 §4 新增 L5「动作分割」+ L6「动作识别」（原 L5 身份识别 → **L7**、L6 出口 → **L8**）；本 change 只交付 L5，L6 归 `video-feature-latent`
- **依赖**：`identity-action-tokenizer`（提供 `λ`）、`video-feature-latent`（提供行为素/段表征）
- **被依赖**：`spot-check-cli`（报告的"标签 + 起止秒"直接来自本环）
- **`video-feature-latent` 阶段划分需调整**：其"序列层/分词层"目前挂在**阶段三（条件启动）**，按本 change 应**提为主线必要一层**
- 可能引入外部无监督 TAS 代码（需核许可；优先 MIT/Apache）
