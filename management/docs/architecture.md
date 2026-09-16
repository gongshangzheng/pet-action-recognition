---
title: 系统架构：完整结构总览
author: 郑鑫裕
date: 2026-09-16
tags: [架构, 管线, 规划, 进度, 术语]
summary: 完整结构一次讲清——监控视频 → 定位跟踪 → 跟随视角 → 动作表征 → 身份识别 → 应用出口，五阶段详解；含术语表与未来计划分类
id: 6
---

# 系统架构：完整结构总览

> **怎么读这篇**：先用五分钟看 §1 总览表把全貌记住；想深入哪个阶段就跳到对应 §，那里会再指到专篇文档。

## §0 术语表

> 首次出现的术语都集中在这里查一遍；后续正文里就不重复定义。

- **mmaction2**：动作识别（视频分类）开源框架，本仓库用它做训练与推理
- **GroundingDINO**：开放词汇检测器——给它一句文字提示（"cat"），它就能在图里框出物体
- **DINOv2**：自监督训练出来的视觉特征提取器，把图/帧变成长长的一串数字（向量），特点是"同一个东西的向量应该相近"
- **FAISS**：向量相似度检索库，把一堆向量存进去，新来一个向量能快速找出库里最像的前 N 个
- **SAM**：Meta 出品的分割模型，给一个点/框/提示就能把物体边缘精确抠出来
- **OWLv2**：开放词汇检测器，跟 GroundingDINO 思路类似
- **HDBSCAN**：基于密度的聚类算法，把一堆向量自动分成若干簇，不用事先指定要分几类
- **ByteTrack**：经典的多目标跟踪算法，给检测框配上身份 id、维持轨迹
- **CatHuBERT**：借用 HuBERT 语音预训练范式，给视频里"行为素"打伪码再自监督预训练
- **FLOAT**：身份-动作解耦的视频生成方法，本仓库身份 tokens 设计借鉴其思想
- **TiTok**：视觉 tokenizer，用几十个 token 就能表达一张图（而不是动辄几百个 patch token）
- **checkpoint**：训练好的模型权重文件，本仓库放在远程 pet 服务器
- **NAS**：网络存储，本项目指挂载在开发机上的共享磁盘（UCF101 等大语料放这里）
- **RTF**（Real-Time Factor）：推断速度指标，每秒视频时长除以每秒推断时长，0.032 表示处理速度约为实时 30 倍
- **对比学习（contrastive learning）**：核心思想——把"同一类"样本在特征空间里拉近、把"不同类"样本推远的学习方式。训练时构造正样本对（如同一只猫的两帧）与负样本对（不同猫的同帧），优化"正对相似度最大化、负对相似度最小化"。本项目身份标识的核心视角就是对比学习：**同一只猫应该共享同一组身份 tokens（positive invariance），不同猫应该有不同的身份 tokens（negative discrimination）**。猫 Re-ID（DINOv2+FAISS）与身份-动作 Tokenizer 的 track 级 InfoNCE 是同一原理的不同实现。

## §1 完整结构总览

监控视频进来后，沿五个阶段走到应用出口。每阶段一行总结，详情跳到对应章节。

| # | 阶段 | 输入 | 输出 | 核心算法 | 代码落点 | 对应 change / 决策 | 深入 |
|---|---|---|---|---|---|---|---|
| 1 | 定位与跟踪 | 原始监控视频 | 猫在每帧的位置框 + 家具框 + 轨迹 | GroundingDINO 多 prompt 抽样 + 插值 + 运动校正 v5 | `scripts/pet_detect_track.py` | `batch-followcam-extraction` / D1 | [7 号 §1](../wiki/identity-and-retrieval) |
| 2 | 跟随视角生成 | 轨迹 JSON | 512×512 以猫为中心的 H.264 短视频 | follow_adaptive 裁剪 + 尺寸离群过滤 + 沙发漂移渲染层过滤 | `scripts/make_followcam.py` | `batch-followcam-extraction` / D1 | [7 号 §2](../wiki/identity-and-retrieval) |
| 3 | 动作表征 | 跟随视频 | 行为簇 + 命名表 | 窗口特征（VideoMAE v1 / DINOv2+帧差 / MammalNet / V-JEPA 2）→ UMAP+HDBSCAN；路线 W CatHuBERT | `scripts/discover_behaviors.py`（计划） | `video-feature-latent` | 本篇 §4 |
| 4 | 身份识别与提取 | 任意阶段输出 | "这只猫是谁 / 这个物体是什么" | 检索式（DINOv2+FAISS，对比学习视角） 或 身份-动作 Tokenizer（track InfoNCE） | `scripts/register_cats.py`（计划） | `registry-retrieval` / `identity-action-tokenizer` | [7 号](../wiki/identity-and-retrieval) / [8 号](../wiki/identity-tokenizer) |
| 5 | 应用出口 | 隐空间表征 | 抽查报告 / 异常告警 | `scripts/spot_check_actions.py`（计划）+ 异常评分原型 | — | `spot-check-cli` / `behavior-anomaly-detection` | 本篇 §6 |

**一句话总览**：把监控视频切成"以猫为中心的小片"→ 给每片学一个行为表征 → 用表征做检索或异常检测，最终产品是"某时段某猫在做什么"的报告。

## §2 定位与跟踪（索引）

把视频里每只猫的位置逐帧找出来、并维持同一只猫的轨迹 id 是所有下游任务的前提。**为什么不用 ByteTrack 全帧率**、**为什么关键点降级为辅助信号**、运动校正 v5 的参数为什么这样定——展开说明在 [7 号《身份标识与检索》§1](../wiki/identity-and-retrieval)。一句话结论：单猫白天场景下"每 10 帧抽样检测 + 插值 + 必要时校正"已经够用，再叠多层跟踪器是过度工程。

## §3 跟随视角生成

跟随视角是"以猫为中心、固定 512×512 大小、H.264 编码"的视频流。它是后续所有特征学习的**主表示载体**——下游模型拿到的不再是"整张监控画面"，而是"这只猫此刻的画面"。好处：① 模型不用再学"找猫在哪里" ② 分辨率不再被浪费在背景上 ③ 帧间变化幅度集中在猫身上，更利于动作建模。详见 [7 号 §2](../wiki/identity-and-retrieval)。

## §4 动作表征（识别动作）

四候选选型当前都在评估：

| 候选 | 思路 | 状态 |
|---|---|---|
| A | VideoMAE v1 宠物微调 | 实验中（`video-feature-latent` 1.1） |
| B | DINOv2 + 帧间差分 | 实验中（同上） |
| C | MammalNet | 权重可得性待探 |
| D | V-JEPA 2 fpc16 | 新主力，需 `pet_vjepa` 环境（transformers ≥4.55） |

路线 W（CatHuBERT 式行为素迭代预训练）也在并行：先取全语料窗口特征 → k-means K=256 伪行为素 → 小 Transformer 遮窗预测 → 迭代两轮。**四闸门验收**：线性可分性、可命名率、码本健康度、身份泄漏审计（详见 [9 号《研究结论与踩坑》](../wiki/lessons)）。

**为什么先无监督发现**而不是直接套人工标注类别？因为 cats v1 的人工 activity 标注里"伞类"占了一半——意思是人也不知道猫到底分几类活动。让数据自己聚成簇，再人工命名，往往比"先拍脑袋定 5 类"更靠谱。详见 [2 号《数据集全景》§2](../wiki/datasets)。

## §5 身份识别与提取（索引）

两条路线，**共享"对比学习"原理**：

1. **检索式**：猫 Re-ID + 物体实例识别。每只猫/物体拍几张"登记照"→ DINOv2 提特征 → FAISS 索引。新出现一只猫/物体时也提特征，去库里检索最像的——相似度超阈值就算"同一个"。详 [7 号 §3/§4](../wiki/identity-and-retrieval)。
2. **身份-动作 Tokenizer**：FLOAT×TiTok 杂交架构——几十个跨时间共享身份 tokens + 每帧一个动作 latent + 解码器重建。stage B 用 track 级 InfoNCE 显式把对比学习视角落进损失。详 [8 号《身份-动作 Tokenizer 专篇》](../wiki/identity-tokenizer)。

两条路线的相同性质：**同猫跨时间/视角特征要聚到一起（positive invariance）、不同猫/物体要互相区分（negative discrimination）**。抓住这一条，主线就稳了。

## §6 应用出口

两条产品形态：

- **抽查报告**（`spot-check-cli`，前置：`video-feature-latent` 归档）：用户指定"某摄像头某时间段"→ 拉录像 → 预处理 → 隐码 → 输出 JSON/Markdown 报告（标签/起止秒/track_id/登记身份/置信度/在场率/空间状态段）
- **行为异常检测**（`behavior-anomaly-detection`，研究型，延后）：正常 = 高频已命名簇，异常 = 低频簇 / token 转移突变 / 滑窗直方图偏离。候选机制（HDBSCAN 簇 ID 序列、VQ token、马尔可夫、孤立森林）需调研。

生产形态 = **非实时抽查**，不做 7×24 实时监控。原因：猫可能不在画面里，全时实时是浪费；用户关心"那一段到底发生了什么"而不是"每秒钟在干什么"。

## §7 跨切面

- **双环境隔离**：mmaction2 训练环境 vs GroundingDINO/HQSAM/ViTPose 管线环境。GroundingDINO 这套依赖重且与 mmcv 约束冲突风险高，因此 pet 上另起 conda env `plf`（precision livestock farming），管线脚本以 subprocess + env 切换调用，产物落盘交接（NPZ/pkl），不跨环境 import（`pet-motion-latent-pipeline` D5）。
- **petlib 可替换模块架构**：检测/跟踪/关键点三大能力封装在 `petlib/` 下，契约测试保障可替换。
- **决策 ID 全局索引**：D1–D9 分布在各子 change design 里，全局 ID 不变，跨文档引用靠这套索引：
  | ID | 主题 | 位置 |
  |---|---|---|
  | D1 | 检测/跟踪/居中工程形态 | `batch-followcam-extraction/design.md` |
  | D1b | GatedTracker 否决 | `tracker-selection/design.md` |
  | D1c | 候选跟踪器原理 | `tracker-selection/design.md` |
  | D2 | 关键点选型裁定 | `batch-followcam-extraction/design.md` |
  | D2b | HQSAM 定位 | `video-feature-latent/design.md` |
  | D3 | 隐空间架构 | `video-feature-latent/design.md` |
  | D4 | 抽查 CLI | `spot-check-cli/design.md` |
  | D5 | 环境隔离 | `pet-motion-latent-pipeline/design.md` |
  | D6 | petlib 接口 | `pet-motion-latent-pipeline/design.md` |
  | D7 | 身份体系 | `spot-check-cli/design.md` |
  | D8 | 主表示选型 | `video-feature-latent/design.md` |
  | D9 | 登记-检索架构 | `registry-retrieval/design.md` |

## §8 当前进度与未来计划

> 基准日 2026-09-16；进度日常变动看 `management/projects/*/tasks.json`。

### §8.1 未来计划四分类

| 类别 | 内容 |
|---|---|
| **① 主线执行序** | batch-followcam-extraction（5/6，待归档） → video-feature-latent（1/14，1.1 选型中） → spot-check-cli（0/4） |
| **② 条件启动/延后** | tracker-selection（触发：多猫数据出现）、registry-retrieval（触发：用户批准实施）、behavior-anomaly-detection（触发：video-feature-latent 归档 + 用户发起调研） |
| **③ 研究型独立立项** | identity-action-tokenizer（0/9，FLOAT×TiTok 架构，详 [8 号](../wiki/identity-tokenizer)） |
| **④ 已归档** | 16 个 change（见 [1 号《仓库资产盘点》§6](../wiki/repo-inventory) 索引） |

### §8.2 验收闸门与里程碑

- video-feature-latent 四闸门：线性可分性 / 可命名率 / 码本健康度 / **身份泄漏审计**（防止行为表征被身份信号污染）
- identity-action-tokenizer 阶段 A 中期检查点：UCF101 上 z_t 探针 top1@101 类 + 身份 dropout/交换消融
- 11 月中期验收 KPI：来自 2026-08-15 二期计划（当前 P0 精度攻坚进行中，P1 端侧 pipeline 待启动）

### §8.3 二期计划对照

| 阶段 | 内容 | 现状 |
|---|---|---|
| P0 精度攻坚 | 8 月中–9 月底 | 多模型训练 5 个 run **全部 error**，问题在数据/接口；k400 烟测 top1 0.77 已验证管线可跑通 |
| P1 端侧 pipeline | 9 月–11 月中 | 34 段白天批处理已 34/34 完成，验证管线；夜间红外段待处理 |
| P2 部署链路与验收 | 11 月–12 月 | 抽查 CLI/异常检测待启动 |

---

**相关文档**：[1 号《仓库资产盘点》](../wiki/repo-inventory)（资产索引）/ [7 号《身份标识与检索》](../wiki/identity-and-retrieval) / [8 号《身份-动作 Tokenizer 专篇》](../wiki/identity-tokenizer) / [9 号《研究结论与踩坑》](../wiki/lessons)