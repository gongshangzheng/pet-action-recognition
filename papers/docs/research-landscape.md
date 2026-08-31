# 动作识别 × 宠物动作：前沿论文与技术路线调研总结

> 生成：2026-08-29 · 依据 seed-papers-library 变更的两轮调研（3 专题 + 3 专题真实 API 检索，全部条目经 arXiv API 核验）
> 论文库：`papers.db` 212 篇 · 核心清单：[[core-papers]] · 数据库检索方式见文末

---

## 一、领域地图：动作识别的六条技术路线

### 路线 1：双流 / 3D CNN（经典奠基，2014–2019）

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| Two-Stream ConvNets (`1406.2199`) 📌 | 2014 | RGB + 光流双流范式开端 |
| I3D / Kinetics (`1705.07750`) 📌 | 2017 | 把 ImageNet 预训练"膨胀"到视频；建立 Kinetics 预训练→下游迁移范式 |
| SlowFast (`1812.03982`) 📌 | 2019 | 慢语义 + 快运动双路，速度/精度折中长期基准 |
| X3D (`2103.15691`) | 2020 | 逐维扩展的高效 3D CNN |

**现状**：仍是工业界轻量部署的主力；mmaction2 支持完善，预训练权重好获取。
**对本项目**：SlowFast 是 live 实时推理与 speedrun 烟测的默认骨干之一。

### 路线 2：视频 Transformer（2021–2022 的监督王者）

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| TimeSformer (`2102.05095`) | 2021 | 分离时空注意力（Divided ST Attention），纯 Transformer 开端 |
| ViViT (`2103.15691`) | 2021 | 多路 Transformer 变体系统研究 |
| MViTv2 (`2112.01526`) | 2021 | 池化多尺度注意力，MaskFeat 的默认骨干 |
| Video Swin (`2106.13230`) | 2021 | 移位窗口 3D 注意力，多项 SOTA，动物基准（Animal Kingdom）主力骨干 |

**对本项目**：Video Swin 的 Kinetics 预训练权重是**迁移到宠物数据的首选起点**（Animal Kingdom 论文同款骨干，证据链最全）。

### 路线 3：掩码自监督预训练（数据效率之王，2022–2023）⭐ 核心问题一的主攻方向

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| VideoMAE (`2203.12602`) 📌 | 2022 | 90% tube masking；**几千段视频即可预训练**，小数据友好 |
| MaskFeat (`2112.09133`) | 2021 | 预测 HOG 特征而非像素 |
| VideoMAE V2 (`2303.16727`) ⭐ | 2023 | dual masking 缩放到十亿参数；支持**域继续预训练**（domain-adaptive pretraining） |

**关键结论**：VideoMAE 论文证明仅用 ~3.5k 视频（Kinetics 子集）预训练即可接近全量效果——这正是"宠物数据少"场景最需要的性质。
**对本项目**：① 用 Kinetics 预训练 VideoMAE 直接微调猫狗数据（现训练栈已支持）；② 进阶：用 live 模块积累的无标注录像做 V2 式继续预训练。

### 路线 4：图像基础模型适配视频（参数高效，2022–2024）

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| UniFormerV2 (`2211.09552`) | 2022 | CLIP ViT + 轻量时空块，K400 首破 90% |
| AIM (`2302.03024`) ⭐ | 2023 | **冻结**图像 ViT，只训 Adapter 即达视频 SOTA |

**关键结论**：视频知识不需要从头学——图像基础模型 + 少量可训练参数即可。这意味着**小数据集微调时不必全量训练**，Adapter/LoRA 式微调更不易过拟合。
**对本项目**：宠物数据微调优先试 AIM 式参数高效方案；Task-Adapter（`2408.00248`）把它延伸到了 few-shot 场景。

### 路线 5：JEPA / 状态空间等新架构（2024–2025 前沿）

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| V-JEPA (`2404.08471`) / V-JEPA 2 (`2506.09985`) | 2024/25 | 在特征空间（而非像素）预测被掩码区域；V2 引入世界模型 |
| VideoMamba (`2403.06977`) | 2024 | 状态空间模型，线性复杂度处理长时序 |
| MS-Temba (`2501.06138`) / MambaTAD (`2511.17929`) | 2025 | Mamba 用于长视频/时序检测 |
| OpenTAD (`2502.20361`) | 2025 | 时序动作检测统一框架 |

**对本项目**：Mamba 线性复杂度对 live 长时流推理有吸引力，但生态尚早；列为观察项。

### 路线 6：视频多模态大模型（VLM，2023–2026）

| 代表论文 | 年份 | 贡献 |
|---|---|---|
| Video-LLaMA (`2306.02858`) / Video-LLaVA (`2311.10122`) / Video-ChatGPT (`2306.05424`) | 2023 | 视频 + LLM 对话范式开创 |
| Qwen2-VL (`2409.12191`) / Qwen2.5-VL (`2502.13923`) | 2024/25 | 动态分辨率 + M-RoPE，秒级事件定位 |
| InternVideo2 (`2403.15377`) ⭐ / VideoPrism (`2402.13217`) ⭐ | 2024 | 判别式+生成式视频基座；冻结编码器即可做 33 个基准 |

**对本项目**：评测模块已集成 Qwen3-VL（Qwen2.5-VL 同门后继）——VLM 路线与 CNN/Transformer 分类器路线**互补**：前者给自然语言描述/零样本泛化，后者给可控的 top-k 分类与速度。BehaviorVLM（`2603.12176`，已入库）显示免微调 VLM 做行为理解正成为新趋势。

---

## 二、领域地图：动物/宠物动作的三条路线

### 路线 A：姿态驱动（最成熟、生态最好）

```
关键点检测 ──► 轨迹/运动学特征 ──► 行为分类或无监督分割
DeepLabCut → SLEAP → SuperAnimal    MARS/B-SOiD/A-SOiD    MoSeq/Keypoint-MoSeq/VAME
```

- **DeepLabCut**（Nature Neurosci 2018）📌：少样本标注即迁移，动物姿态事实标准
- **SuperAnimal**（`2203.07436`，Nat Commun 2024）📌：**跨物种预训练姿态基础模型，四足（Quadruped）零样本可用**——宠物关键点无需任何标注
- **Keypoint-MoSeq**（Nature Methods 2024）⭐：关键点 + 姿态动力学自动切分行为音节，**无需预定义类别表**即可发现动作
- **A-SOiD**（Nat Methods 2024）：主动学习，极少专家标注得高精度分类器

**对本项目**：SuperAnimal-Quadruped 零样本出关键点 →（a）给视频路线做辅助特征/伪标注；（b）训练骨架轻量分类器（对背景/遮挡更鲁棒）；（c）MoSeq 式无监督发现"猫有多少种动作"，反过来指导标注类别表设计。

### 路线 B：视频像素直分（与本项目主线最贴合）

- **DECADE**（`1803.10827`，CVPR 2018）：最早的狗视频行为数据集+方法
- **DeepEthogram**（eLife 2021）：原始像素监督行为分类流水线
- **AnimalMotionCLIP**（`2505.00569`，2025）：把运动信息嵌入 CLIP 空间
- **基准**：Animal Kingdom（`2204.08129` 📌，850 物种）· MammalNet（`2306.00576` 📌，173 类哺乳动物行为）· APT-36K（`2206.05683`）· AP-10K（`2108.12617`）· CVB 牛行为（`2305.16555`）· MammAlps（`2503.18223`）· KABR 无人机（`2510.02030`）
- **综述**：**Coarse to Fine-Grained Animal Action Recognition**（`2506.01214`，2025）——领域地图，优先阅读

**空白信号**：arXiv 上 `pet action recognition` 检索结果为空；猫/狗细粒度家养宠物动作（踩奶、踩便、甩尾）没有公开基准——**这是本平台的数据护城河所在**。

### 路线 C：跨物种迁移与数据稀缺（对应两大核心问题）

**核心问题二：人类模型 → 动物，证据链完整 ✅**

| 证据 | 结论 |
|---|---|
| Cross-Domain Adaptation for Animal Pose（`1908.05806`，ICCV 2019） | 人体姿态域 → 动物域无监督适应可行 |
| APT-36K（`2206.05683`） | 人体预训练姿态模型迁移动物 **显著优于从头训练** |
| ViTPose++（`2212.04246`）⭐ | 人体姿态基础模型直接扩展到动物数据集 |
| MammalNet（`2306.00576`） | 量化了 Kinetics 人类动作预训练 → 动物行为识别的迁移增益 |
| Purrturbed but Stable（`2511.02404`） | 人-猫图像表征不变性的系统研究 |
| ZebraPose → 奶牛（`2510.22618`） | 跨物种迁移在畜牧场景落地验证 |

**核心问题一：数据稀缺，排序后的对策** 🥇🥈🥉

1. **自监督域继续预训练**（VideoMAE V2 掩码续训，用 live 无标注录像）——数据效率最大单点投入
2. **参数高效微调**（AIM/Task-Adapter 式 Adapter）——同等数据下更不易过拟合
3. **SuperAnimal 零样本姿态桥接**——不增加视频标注，直接引入骨架监督信号
4. few-shot 元学习（OTAM `1906.11415` / TRX `2101.06184` / HyRSM `2204.13423` / MoLo `2304.00946`）——**不推荐正面硬刚**：这些方法假设有充足 base 类，增益集中在 1–5 shot 极限；每类攒 20–50 段直接微调即胜出。作为长尾类别的兜底范式保留
5. 合成数据（SMAL `1611.07700` / BARC `2203.15536` / AP-CAP `2504.00394`）——姿态保真尚可、**动作动态保真不足**，仅作辅助

---

## 三、可直接落地的结论（按项目维度）

### 训练维度
1. **主路径已验证**：Kinetics 预训练 VideoMAE / Video Swin → `quadruped_cats_v1` 全量微调（mmaction2 registry 现成支持），预期显著优于从头训练
2. **下一步增量**：VideoMAE V2 式掩码继续预训练，语料 = live 模块积累的无标注监控录像
3. **小数据技巧**：先用 AIM 式 Adapter 微调对比全量微调；模型选择上 VideoMAE-S/B 量级（非十亿级）更合适

### 评测维度
4. 对标协议：Animal Kingdom（动作识别 acc）+ MammalNet（行为理解）的报告口径；自家数据沿用 speedrun 烟测 + run_test top1/top5
5. 骨架路线可用 AP-10K / APT-36K 的关键点模型先做 sanity check，再上自家分类

### Live / 推理维度
6. 实时性预算：SlowFast / X3D（CNN 系）当前仍是延迟最优；VideoMamba 线性复杂度值得跟踪
7. 边缘部署参考 TinyML 畜牧方案（`2504.11467`）：量化 + Edge TPU 在 livestock 场景已验证可行

### VLM 维度
8. Qwen3-VL 集成继续走：Qwen2.5-VL 的秒级时序定位能力与"动作片段在何时发生"问答天然匹配
9. AmadeusGPT（`2307.04858`）范式值得抄：**自然语言 → 生成行为分析代码**，可降低团队使用姿态流水线的门槛

### 数据/标注策略
10. 类别表设计先用 Keypoint-MoSeq/B-SOiD 无监督聚类"发现"自然动作簇，再人工归并命名——避免拍脑袋定义类别
11. 标注优先级：每类先攒 20–50 段（全量微调够用）→ 长尾类别才考虑 few-shot 兜底
12. **风险**：动物特有动作（踩奶、甩尾）在人类动作空间无对应类，微调后需保留未知类检测能力（长尾 + 开放集）

---

## 四、论文索引与检索

- **核心 20 篇（pinned 8 + core 12）**：[[core-papers]] · `papers/config/core_papers.json`
- **全量 212 篇**：`GET /api/papers?search=<关键词>` · 前端 http://localhost:3000
- **分类检索**：`paper_categories` 表（action_recognition / pet_action_recognition / few_shot_action_recognition / pose_estimation / skeleton_action_recognition / video_foundation_model / survey / temporal_action_detection）
- **调研原始数据**：`openspec/changes/seed-papers-library/research-verified.json`（全部条目含核验状态）
- **已知缺口**：43 篇 manual 条目无摘要（Nature/eLife 系，arXiv 无版本）；arXiv 解禁后重跑导入可升级全部元数据（任务 2.5）
