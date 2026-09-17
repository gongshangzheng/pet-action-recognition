---
title: 系统架构：结构 · 设计 · 进度
author: 郑鑫裕
date: 2026-09-17
tags: [架构, 管线, 设计, 决策, 术语, 进度, Mermaid]
summary: 唯一架构文档——监控视频 → 定位跟踪 → 跟随视角 → 背景移除 → 动作表征 → 身份识别 → 应用出口；含术语表、端到端 Mermaid 结构图、分层设计决策、16 项待定选择、决策索引与当前进度
id: 6
---

# 系统架构：结构 · 设计 · 进度

> **本文是所有「结构 / 设计」问题的唯一入口**：术语表（§0）→ 端到端总图（§1）→ 分层设计（§2）→ 跨切面（§3）→ 待定选择（§4）→ 决策索引（§5）→ 演进记录（§6）→ 进度（§7）。
>
> **深入设计**：模型层 → [8 号《身份-动作 Tokenizer》](./identity-tokenizer.md)；身份两条路线原理 → [7 号《身份标识与检索》](./identity-and-retrieval.md)；数据集 → [2 号《数据集全景》](./datasets.md)；训练 → [4 号《训练体系》](./training-guide.md)。

## §0 术语表

> 首次出现的术语都集中在这里查一遍；后续正文里就不重复定义。

- **mmaction2**：动作识别（视频分类）开源框架，本仓库用它做训练与推理
- **GroundingDINO**：开放词汇检测器——给它一句文字提示（"cat"），它就能在图里框出物体
- **DINOv2**：自监督训练出来的视觉特征提取器，把图/帧变成长长的一串数字（向量），特点是"同一个东西的向量应该相近"
- **FAISS**：向量相似度检索库，把一堆向量存进去，新来一个向量能快速找出库里最像的前 N 个
- **SAM / SAM2**：Meta 出品的分割模型，给一个点/框/提示就能把物体边缘精确抠出来；SAM2 加了记忆注意力，能沿时间传播掩码
- **OWLv2**：开放词汇检测器，跟 GroundingDINO 思路类似
- **HDBSCAN**：基于密度的聚类算法，把一堆向量自动分成若干簇，不用事先指定要分几类
- **ByteTrack**：经典的多目标跟踪算法，给检测框配上身份 id、维持轨迹
- **CatHuBERT**：借用 HuBERT 语音预训练范式，给视频里"行为素"打伪码再自监督预训练
- **TivTok**：视频 tokenizer，用 **TIV**（时间不变，管身份）+ **TV**（时间可变，管动作）两组 token 表达一段视频；其 SIF 机制靠注意力范围差异实现分解
- **FLOAT / LIA**：身份-动作解耦方法；运动 latent = 正交运动基的线性组合 `z_t = Σ λ_m·v_m`
- **TiTok**：视觉 tokenizer，用几十个 token 就能表达一张图（而不是动辄几百个 patch token）
- **正交运动基**：M 个两两正交的运动方向（QR 硬约束）；每帧的动作 = 这些方向的加权和，系数 `λ_m(t)` 可读
- **checkpoint**：训练好的模型权重文件，本仓库放在远程 pet 服务器
- **NAS**：网络存储，本项目指挂载在开发机上的共享磁盘（UCF101 等大语料放这里）
- **RTF**（Real-Time Factor）：推断速度指标，每秒视频时长除以每秒推断时长，0.032 表示处理速度约为实时 30 倍
- **对比学习（contrastive learning）**：核心思想——把"同一类"样本在特征空间里拉近、把"不同类"样本推远。本项目身份标识的核心视角：**同一只猫应共享同一组身份 tokens（positive invariance），不同猫应有不同身份 tokens（negative discrimination）**。猫 Re-ID（DINOv2+FAISS）与身份-动作 Tokenizer 的 track 级 InfoNCE 是同一原理的不同实现。

## §1 端到端设计总图

整条链路的目标：把监控视频变成"某时段某只猫在做什么"的结构化报告。六个环节，每个环节的输出都是下一环节的输入（第 4/5 环节并列消费第 3 环节）。

```mermaid
flowchart TD
    V[监控视频<br/>白天彩色 / 夜间红外] --> S1

    subgraph S1["① 定位与跟踪"]
        A1[GroundingDINO 抽样检测] --> A2[插值<br/>可选运动校正]
    end

    S1 --> S2

    subgraph S2["② 跟随视角生成"]
        B1[follow_adaptive 跟随裁剪] --> B2[512×512 H.264 短片]
    end

    S2 --> S3

    subgraph S3["③ 背景移除"]
        C1[SAM2 掩码传播] --> C2[猫本体 + 黑背景]
    end

    S3 --> S4
    S3 --> S5

    subgraph S4["④ 动作表征"]
        D1[AdapTok 基座<br/>+ TivTok SIF 双 token] --> D2[连续潜变量<br/>无量化]
        D2 --> D3[FLOAT/LIA 正交运动基]
    end

    subgraph S5["⑤ 身份识别"]
        E1[DINOv2 + FAISS 检索]
        E2[TIV tokens + track InfoNCE]
    end

    S4 --> S6
    S5 --> S6

    subgraph S6["⑥ 应用出口"]
        F1[抽查报告 CLI]
        F2[实时监控 SSE]
        F3[行为异常检测]
    end
```

**一句话总览**：把监控视频切成"以猫为中心的小片"→ 抠掉背景 → 给每片学一个可分解的动作表征 → 用表征做检索或异常检测，最终产品是"某时段某猫在做什么"的报告。

**设计要点**：第 3 环节（背景移除）是为第 4 环节服务的——followcam 的相机随猫移动，背景持续变化，若不剥离，动作通道会把相机运动当成动作学进去。空间上下文（在床上/地上）已由第 1 环节的空间关系状态层独立承担，因此抠像不丢信息。

## §2 分层设计

### §2.1 L1 定位与跟踪

| 项 | 设计 |
|---|---|
| 输入 | 原始监控视频（白天彩色 / 夜间红外） |
| 输出 | 每帧猫框 + 家具框 + 轨迹 id（JSON） |
| 算法 | GroundingDINO 多 prompt 抽样检测（每 10 帧）→ 插值 → **（可选）运动校正**（默认禁用） |
| 代码 | `scripts/pet_detect_track.py`、`scripts/pet_multi_detect.py` |
| 关键决策 | 不用 ByteTrack 全帧率（单猫白天场景过度工程）；关键点降级为辅助信号 |
| 空间语义 | 猫框底边中点落入家具框 → `cat on {家具}`，否则 `on floor`；≥1.5s 迟滞 |
| 状态 | ✅ 已归档（`multi-object-detect-gate`、`batch-followcam-extraction`）|

**为什么不用 ByteTrack 全帧率**：单猫白天场景下"每 10 帧抽样检测 + 插值"已经够用，再叠多层跟踪器是过度工程。

**运动校正（可选）**：猫被柱子/家具遮一下又出来、重新框到时位置可能跳变，运动校正让位置平滑。它是**插值之后的独立开关，默认禁用**（治标有限，关键帧丢就让它丢，渲染层过滤兜底）。参数与实测见 [9 号《研究结论与踩坑》§4.1](./lessons.md)。展开说明见 [7 号 §1](./identity-and-retrieval.md)。

### §2.2 L2 跟随视角生成

| 项 | 设计 |
|---|---|
| 输入 | 轨迹 JSON |
| 输出 | 512×512 以猫为中心的 H.264 短片 |
| 算法 | follow_adaptive 自适应裁剪 + 尺寸离群过滤 + 渲染层漂移过滤 |
| 代码 | `scripts/make_followcam.py`、`scripts/pet_batch_run.py` |
| 状态 | ✅ 34/34 段完成（共 14.7 分钟）|

**为什么它是主表示载体**：跟随视角是后续所有特征学习的载体——下游模型拿到的不再是"整张监控画面"，而是"这只猫此刻的画面"。好处：① 模型不用再学"找猫在哪里" ② 分辨率不再被浪费在背景上 ③ 帧间变化幅度集中在猫身上，更利于动作建模。详见 [7 号 §2](./identity-and-retrieval.md)。

### §2.3 L3 背景移除

```mermaid
flowchart LR
    X1[跟随视频] --> X2[SAM2<br/>检测框作 prompt]
    X2 --> X3[逐帧掩码传播]
    X3 --> X4{质量闸门}
    X4 -->|正常| X5[掩码膨胀 + 黑背景合成]
    X4 -->|面积突变/漂移| X6[回退最近有效掩码<br/>并标记告警]
    X6 --> X5
    X5 --> X7[猫本体视频]
```

| 项 | 设计 |
|---|---|
| 输入 | 跟随视频 + 猫检测框（复用 L1 产物）|
| 输出 | 仅含猫本体、背景置黑的视频（帧数/帧率/分辨率对齐，不覆盖原视频）|
| 主选 | **SAM2**——接受 box prompt、输出二值 mask、memory attention 抗帧间闪烁、Apache-2.0 许可、零样本含动物评测 |
| 备选 | BiRefNet（图像级，逐帧会闪）；RVM **已否决**（人物域训练 + GPL-3.0 传染）|
| 质量兜底 | 掩码面积突变 / 时序漂移 / 检测丢失 → 回退并告警，不静默输出脏数据 |
| 状态 | 📋 `pet-background-removal` 已立项（4/4 规划，待实施）|

### §2.4 L4 动作表征（模型层）

这是全项目最复杂的环节，深入设计见 [8 号《身份-动作 Tokenizer》](./identity-tokenizer.md)。此处只给结构骨架：

```mermaid
flowchart TD
    M1[猫本体视频<br/>16 帧窗口] --> M2[ViT 编码器<br/>12 层 / 768 维 / patch 4×8×8]
    M2 --> M3{TivTok SIF<br/>非对称注意力 scope}

    M3 -->|attend 全部帧| M4[TIV tokens<br/>时间不变 → 身份]
    M3 -->|只 attend 本帧| M5[TV tokens<br/>时间可变 → 动作]

    M4 --> M6[连续潜变量<br/>无量化 · KL 正则]
    M5 --> M6

    M5 --> M7[FLOAT/LIA 正交运动基<br/>z_t = Σ λ_m·v_m]
    M7 --> M8[λ 基元强度序列<br/>可解释动作表示]

    M6 --> M9[解码器<br/>TIV + TV_t 重建]
    M4 --> M10[身份通道<br/>track InfoNCE]
```

| 项 | 设计 |
|---|---|
| 基座 | **AdapTok**（MIT，12 层 / 768 维 / patch 4×8×8，与 TivTok 同形，自带完整 attention mask 框架）|
| 双 token | TivTok 的 SIF：TIV 看全部帧（身份）、TV 只看本帧（动作），分解由架构诱导而非损失约束 |
| 量化器 | **无量化**（连续潜变量 + KL 正则，TiTok VAE 模式同思路）；SoftVQ 软码本仅作备用正则 |
| 动作通道 | FLOAT/LIA 正交运动基：`z_t = Σ λ_m·v_m`，基由 QR 每次前向正交化；λ 曲线即动作基元强度 |
| 离散化 | **不在帧级做**——交给行为聚类（HDBSCAN + 命名，序列级）|
| 身份通道 | TIV 池化 + track 级 InfoNCE（同猫拉近、异猫推远）|
| 监督 | 重建（L1 + 感知 + 对抗）+ 动作伪行为素 CE + 身份 InfoNCE + 跨猫交换重建（解耦验证）|
| 两阶段 | A：UCF101（13320 段，NAS）验证架构 → B：猫语料迁移 + 身份监督 |
| 状态 | ⏳ 主线 2.3（规划完成，待实施）|

**为什么先无监督发现行为**，而不是直接套人工标注类别？因为 cats v1 的人工 activity 标注里"伞类"占了一半——意思是人也不知道猫到底分几类活动。让数据自己聚成簇、再人工命名，往往比"先拍脑袋定 5 类"更靠谱。详见 [2 号《数据集全景》§2](./datasets.md)。

**验收四闸门**：线性可分性、可命名率、码本健康度、**身份泄漏审计**（防止行为表征被身份信号污染）。详见 [9 号《研究结论与踩坑》](./lessons.md)。

### §2.5 L5 身份识别

两条并行路线，**共享同一原理**：同猫跨时间/视角要聚到一起，不同猫要区分开。

```mermaid
flowchart LR
    subgraph R1["路线一：检索式"]
        P1[登记照] --> P2[DINOv2 提特征] --> P3[FAISS 索引]
        P4[新画面] --> P5[提特征] --> P6[最近邻检索]
        P3 --> P6
        P6 --> P7{"相似度超过阈值?"}
        P7 -->|是| P8[判定为同一只]
        P7 -->|否| P9[新个体]
    end
    subgraph R2["路线二：Token 式"]
        Q1[猫视频] --> Q2[TIV tokens] --> Q3[InfoNCE 训练]
        Q3 --> Q4[身份嵌入]
    end
```

| 路线 | 机制 | 特点 | 状态 |
|---|---|---|---|
| 检索式 | DINOv2 特征 + FAISS 最近邻 | 零训练、可解释、易上线 | ⏸️ `registry-retrieval`（待批准）|
| Token 式 | TIV tokens + track InfoNCE | 与动作表征同源、联合训练 | ⏳ 随 L4 产出 |

两条路线的相同性质：**同猫跨时间/视角特征要聚到一起（positive invariance）、不同猫/物体要互相区分（negative discrimination）**。抓住这一条，主线就稳了。详见 [7 号 §3/§4](./identity-and-retrieval.md)。

### §2.6 L6 应用出口

| 形态 | 输入 | 输出 | 状态 |
|---|---|---|---|
| 抽查报告 | 指定时段录像 | JSON/Markdown（标签/起止秒/track/身份/置信度/在场率/空间状态）| ⏳ `spot-check-cli` 规划完成 |
| 实时监控 | live 视频流 | SSE 推送状态（秒级）| ⏳ 同上（复用 live 模块流式设施）|
| 异常检测 | 行为表征序列 | 异常告警 | ⏸️ `behavior-anomaly-detection`（研究型，延后）|

**形态修订（2026-09-16）**：由"仅非实时抽查"修订为**实时监控 + 非实时抽查双模式**，两者共享同一份行为簇字典（离线发现、在线分配）。

异常检测的候选机制：正常 = 高频已命名簇，异常 = 低频簇 / token 转移突变 / 滑窗直方图偏离（HDBSCAN 簇 ID 序列、VQ token、马尔可夫、孤立森林待调研）。

## §3 跨切面设计

### §3.1 双环境隔离

依赖冲突无法在一个环境里共存，因此按用途切分：

```mermaid
flowchart LR
    subgraph ENV1["plf 环境"]
        G1[GroundingDINO]
        G2[关键点 / 分割]
    end
    subgraph ENV2["pet_tokenizer 环境"]
        T1[tokenizer 训练 / 推理]
    end
    subgraph ENV3["mmaction2 环境"]
        M1[传统动作识别训练]
    end
    D[产物落盘<br/>NPZ / pkl / mp4] --> ENV1
    D --> ENV2
    D --> ENV3
```

**原则**：环境间**不 import 跨用**，靠产物落盘交接；管线脚本用 subprocess + 环境切换调用。GroundingDINO/HQSAM/ViTPose 这套依赖重且与 mmcv 约束冲突风险高，所以 pet 上另起 conda env `plf`（决策 D5）。

### §3.2 可替换模块（petlib）

检测 / 跟踪 / 关键点三大能力封装在 `petlib/` 下，以抽象基类 + 契约测试保障可替换（13 项契约测试通过）。

### §3.3 部署与数据拓扑

```mermaid
flowchart LR
    NAS[(NAS<br/>UCF101 / 大语料)] --> LOCAL[本地开发机<br/>代码 + 规划 + 小产物]
    LOCAL -->|git push| PET[pet 服务器<br/>RTX 4090 ×2]
    PET -->|训练 / 推理| RESULTS[results/ 产物]
    RESULTS --> LOCAL
```

**纪律**：远程 = 只读执行环境，所有文件改动在本地完成、经 git 同步；GPU 任务前查占用；产物只写项目路径。

## §4 目前面临的选择

> 下表是**当前未定**的设计选择。已定的不再列出（见 §5 决策索引）。

### §4.1 背景移除（L3）

| # | 选择项 | 选项 | 倾向与理由 |
|---|---|---|---|
| C1 | 分割模型 | SAM2 / BiRefNet / RVM | **SAM2**——box prompt 可直接复用现有检测框；memory attention 正对"背景随相机动"；Apache 许可干净。RVM 有人物域 + GPL 双重风险（已否决）|
| C2 | 掩码形态 | 二值 / alpha | **二值**——下游是特征提取，不需要羽化 |
| C3 | 多猫场景 | 掩码并集 / 逐猫分离 | 待定：并集简单，但身份训练需要单猫片段 |

### §4.2 模型架构（L4）

| # | 选择项 | 选项 | 倾向与理由 |
|---|---|---|---|
| C4 | 编码器初始化 | AdapTok 权重 / SoftVQ-VAE 权重 / 从零训 | **AdapTok 权重**（同形、MIT）；从零训可接受（SoftVQ 权重为次选）|
| C5 | 量化器 | **无量化（连续 + KL）** / SoftVQ 软正则 / FSQ / VQ | **已定：无量化**（2026-09-17）——下游全需连续表征；先例：TiTok 官方 VAE 模式（重建反优于 VQ：0.84 vs 1.49）、SoftVQ-VAE 本就是 continuous tokenizer、MAR/AR-video 去 VQ 先例 |
| C6 | TIV : TV 比例 | 3:1 / 1:1 / 1:3 等 | **3:1**（TivTok 实测口径：TIV 96 + TV 32 @16 帧）|
| C7 | token 数量 | N_TIV / N_TV / 正交基元数 M | 待定：起点 N_TIV 96、N_TV 2/帧、M 20–32，做缩放消融 |
| C8 | 正交基实现 | QR（`torch.linalg.qr`）/ 经典 Gram-Schmidt | **QR**——与 LIA/FLOAT 代码一致，数值更稳；论文称 Gram-Schmidt 指同一数学对象 |
| C9 | 基的符号 | 自由 / 训练后固定 | 冻结基时必须固定符号，否则 λ 语义漂移 |
| C10 | 对齐教师 | 无 / DINOv3（外观）/ V-JEPA 2 或 InternVideo2（动作）/ 加 SACP | 待定：先不加（纯架构解耦），训练不稳再上 DeRA 式对齐 |
| C11 | 训练粒度 | 阶段 A1 冻结骨干 → A2 端到端 | **两段都做**，实测 A1 是否够用 |
| C12 | 输入规格 | 128 vs 256 分辨率；16 帧 | 待定：256 贴近 TivTok 口径，128 省算力 |
| C13 | 自适应 token 预算 | 用 AdapTok 的 block-mask + ILP / 不用 | 待定：作为后续增强，本期固定预算 |

### §4.3 身份与出口（L5/L6）

| # | 选择项 | 选项 | 倾向与理由 |
|---|---|---|---|
| C14 | 身份监督形式 | InfoNCE / ArcFace / 两者 | **InfoNCE 为主**（与对比学习主线一致），ArcFace 作增强 |
| C15 | 实时模式延迟预算 | 秒级 / 更高 | 待定（`spot-check-cli` 的 Open Question）|
| C16 | 异常检测机制 | HDBSCAN 簇序列 / VQ token / 马尔可夫 / 孤立森林 | 待调研（研究型 change）|

## §5 设计决策索引

已定决策的全局 ID（跨文档引用不变）：

| ID | 主题 | 位置 |
|---|---|---|
| D1 | 检测/跟踪/居中工程形态 | `batch-followcam-extraction/design.md` |
| D1b/D1c | GatedTracker 否决 / 候选跟踪器原理 | `tracker-selection/design.md` |
| D2 | 关键点选型裁定（降级为辅助）| `batch-followcam-extraction/design.md` |
| D2b | HQSAM 定位 | `video-feature-latent/design.md` |
| D3 | 隐空间架构 | `video-feature-latent/design.md` |
| D4 | 推理形态（抽查 + 实时双模式）| `pet-motion-latent-pipeline/design.md` |
| D5 | 环境隔离 | `pet-motion-latent-pipeline/design.md` |
| D6 | petlib 接口 | `pet-motion-latent-pipeline/design.md` |
| D7 | 身份体系 | `spot-check-cli/design.md` |
| D8 | 主表示选型 | `video-feature-latent/design.md` |
| D9 | 登记-检索架构 | `registry-retrieval/design.md` |

**模型层设计决策**（T-A1…T-A9，含两阶段数据、损失、token 骨架、正交基、评测矩阵）见 `openspec/changes/identity-action-tokenizer/design.md`；**抠像层**（二值掩码、SAM2 选型、质量闸门、输出规格、批处理）见 `openspec/changes/pet-background-removal/design.md`。

## §6 设计演进记录

| 日期 | 变更 | 影响 |
|---|---|---|
| 2026-09-15 | 关键点降级为辅助信号；K400 人类先验不适用 → 候选重构 | L1/L4 |
| 2026-09-15 | 运动校正参数定稿（可选开关，默认禁用）| L1 |
| 2026-09-16 | 推理形态由"仅抽查"修订为**抽查 + 实时双模式** | L6 |
| 2026-09-16 | 路线顺序调整：**编码器优先**——先建 tokenizer，再做行为发现 | L4 |
| 2026-09-16 | 架构收敛：TivTok（骨架）+ FLOAT/LIA（正交基）+ AdapTok（基座）| L4 |
| 2026-09-16 | 新增 L3 背景移除环节（独立 change）| 全链路 |
| 2026-09-16 | 方案否证记录：参考帧机制、纯 register tokens、双独立编码器、模型内 VQ 码本 | L4 |
| **2026-09-17** | **全面去量化**：移除 VQ/SoftVQ，改连续潜变量 + KL；正交仅加在运动基（M≈20–32 方向），不加在码本（R^d 中最多 d 个正交向量，码本 8192 个不可能正交）；离散化交给序列级行为聚类 | L4 |
| 2026-09-17 | 先例核查（联网）：TiTok 官方 `quantize_mode: "vae"` 已有预训练权重且重建更好（0.84 vs 1.49）；SoftVQ-VAE 论文标题即 "Continuous Tokenizer"；MAR / AR-Video-w/o-VQ 跨域印证 | L4 |
| 2026-09-17 | **本文合并**：原 6 号《系统架构》+ 12 号《架构设计》合为一篇，消除重复与漂移 | 全篇 |

## §7 当前进度与未来计划

> 基准日 2026-09-17；执行中进度看 `management/projects/*/tasks.json`，change 状态以 `openspec/changes/pet-motion-latent-pipeline/tasks.md` §2 路线图为准。

### §7.1 子 change 路线图

| # | 子 change | 内容 | 依赖/触发 | 状态 |
|---|---|---|---|---|
| 2.1 | `multi-object-detect-gate` | 多目标检测（五类）+ 空间关系状态层 | — | ✅ 已归档（2026-09-15）|
| 2.2 | `batch-followcam-extraction` | 全量批处理 34 段 + followcam 产出 | 2.1 | ✅ 34/34 闭环（14.7 分钟），**待归档** |
| 2.3 | `identity-action-tokenizer` | 🔬 升主线（encoder 优先）：TivTok SIF 双 token + FLOAT/LIA 正交运动基（UCF101→猫语料两阶段）| 2.2 | ⏳ 待 2.2 归档 |
| 2.3b | `pet-background-removal` | 猫本体抠像——消除背景运动对动作通道的污染 | 可并行 2.3 阶段 A；**2.3 阶段 B 前必须完成** | 📋 已创建待启动 |
| 2.4 | `video-feature-latent` | 消费 2.3 编码器做行为发现 + 探针评测（现成 backbone 降为回退）| 2.3 | ⏳ 待 2.3 |
| 2.5 | `spot-check-cli` | 抽查 CLI + 实时监控模式 + 猫身份登记 | 2.4 | ⏳ 待 2.4 |
| 4A | `tracker-selection` | 跟踪器选型（多猫场景）| 多猫数据出现 | ⏸️ 延后 |
| 4B | `registry-retrieval` | 碗/摄像头实例识别 + 猫 Re-ID | 用户批准实施 | ⏸️ 延后 |
| 4C | `behavior-anomaly-detection` | 行为异常检测（研究型）| 2.4 归档 + 用户发起 | ⏸️ 延后 |

**主线一句话**：`2.2 归档` → `2.3 编码器（+2.3b 抠像并行）` → `2.4 行为发现` → `2.5 抽查出口`。

### §7.2 验收闸门与里程碑

- **video-feature-latent 四闸门**：线性可分性 / 可命名率 / 码本健康度 / 身份泄漏审计
- **identity-action-tokenizer 阶段 A 中期检查点**：UCF101 上 z_t 探针 top1@101 类 + 身份 dropout/交换消融
- **11 月中期验收 KPI**：来自 2026-08-15 二期计划（P0 精度攻坚进行中，P1 端侧 pipeline 待启动）

### §7.3 二期计划对照

| 阶段 | 内容 | 现状 |
|---|---|---|
| P0 精度攻坚 | 8 月中–9 月底 | 多模型训练 5 个 run **全部 error**，问题在数据/接口；k400 烟测 top1 0.77 已验证管线可跑通 |
| P1 端侧 pipeline | 9 月–11 月中 | 34 段白天批处理已 34/34 完成，验证管线；夜间红外段待处理 |
| P2 部署链路与验收 | 11 月–12 月 | 抽查 CLI/异常检测待启动 |

## §8 相关文档

- [8 号《身份-动作 Tokenizer》（模型层深入设计）](./identity-tokenizer.md)
- [7 号《身份标识与检索》](./identity-and-retrieval.md)（定位追踪 / 猫 Re-ID / 物体标识）
- [1 号《仓库资产盘点》](./repo-inventory.md)（资产索引 + 归档 change 清单）
- [2 号《数据集全景》](./datasets.md) / [3 号《模型》](./models.md) / [4 号《训练体系》](./training-guide.md)
- [9 号《研究结论与踩坑》](./lessons.md) / [10 号《第三方项目借鉴》](./third-party-notes.md) / [11 号《交接与协作指南》](./handover-guide.md)
- 远程执行纪律：`.claude/skills/remote-servers/`、`.claude/skills/remote-server-discipline/`
