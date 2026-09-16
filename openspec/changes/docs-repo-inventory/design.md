# Design: docs-repo-inventory

## Context

文档现状（2026-09-16 盘点）：

| 位置 | 文件 | 状态 |
|---|---|---|
| `management/docs/`（wiki，9 篇） | mmaction2-overview(183行)、model-onboarding(145行)、keypoint-extraction-pitfalls(142行)、third-party-remix-petra(131行)、live-realtime-inference-plan(118行)、live-page-integration-plan(115行)、detection-annotation-taxonomy(98行)、third-party-pet-videos(108行)、tasks(30行) | 多数活跃；live 两篇已落地；tasks.md 停在 7 月 |
| `docs/plans/`（2 篇） | 2026-07-13 mmaction2 训练集成计划、2026-08-15 二期研究计划 | 前者已落地；后者部分过时（P0 已完成大半） |
| `docs/` | 宠物动作识别研究计划.docx（二进制） | 保留 |
| 根目录 | README.md（118 行） | 缺 training/live/speedrun/pipeline 等半数模块说明 |
| 各子目录 | datasets/quadruped_action/README.md、management/README.md、templates/README.md 等 | 有效目录说明，保留不动 |

散落的知识源（新文档必须收录但现存文档没有的）：`results/` 各 json/md 里的指标与结论、openspec 总管 change（pet-motion-latent-pipeline design 裁决 D1–D9 + 7 个子 change 的任务进度/验收闸门）、训练 run 记录（metrics.json 5 个 run）、批处理报告（batch_report.md 三率+告警结案）。

Wiki 机制（`server/routers/management.py`）：递归扫描 `management/docs/**/*.md`，解析 YAML frontmatter（title/author/date/tags/summary/id），slug=文件名（限 `^[a-zA-Z0-9_/-]+$`），按数字 id 升序、无 id 者按日期倒序排后。现存 9 篇均无 id 字段。

与现有知识库的分工：`.claude/skills/`（15 个）是 agent 操作指南、`AGENTS.md` 是 agent 仓库纪律、wiki 是**人读的项目知识沉淀**——三者不互相复制内容，wiki 用链接引用 skills。

## Goals / Non-Goals

**Goals**
- 一份《仓库资产盘点》作为全库唯一入口，回答"有什么重要内容/数据、在哪、什么状态"
- 一套主题统一、带 frontmatter、id 有序的 wiki 文档（11 篇），吸收全部现存文档的有效信息；其中：
  - **身份标识与检索**一篇整合定位追踪+猫 Re-ID+RAG 式物体标识三件事，用对比学习作统一视角
  - **系统架构**讲完整结构；**身份-动作 Tokenizer 专篇**单独成篇
  - **交接与协作指南**使新协作者不依赖口口相传即可上手
- 写作风格 = 老师腔：术语首次出现给定义，不假设读者懂；类比与示例优先；适用全部 11 篇
- 每篇被删/被吸收文档有明确"信息去向"记录，重要信息零丢失

**Non-Goals**
- 不清理顶层散落文件（另立 change `chore-toplevel-cleanup` 处理），仅在盘点文档登记
- 不改任何代码、数据库、数据集、results 产物
- 不动 `.claude/skills/`、`AGENTS.md`、`openspec/` 本体
- 不整理 management/ 下日报/周报/会议等结构化业务数据

## Decisions

### D1 文档集落位与命名

统一放 `management/docs/`（web Wiki 页自动可见）。文件名 ASCII kebab-case（slug 正则限制），frontmatter 必带 `id: 1..11` 使新文档排 wiki 最前。

### D2 目标文档集总览（11 篇）

| id | 文件 | 标题 | 一句话定位 | 主要来源 |
|---|---|---|---|---|
| 1 | repo-inventory.md | 仓库资产盘点 | 全库唯一入口：有什么/在哪/什么状态 | 新写（D4.1） |
| 2 | datasets.md | 数据集全景 | 当前所有数据集：规模/标注/位置/状态/用途 | 新写 + detection-annotation-taxonomy 全文 |
| 3 | models.md | 模型 | 重要模型逐个条目：简介 + 实测结果 | 新写 + model-onboarding + results/*.json |
| 4 | training-guide.md | 训练体系 | 怎么训：mmaction2 机制/四模式/registry/远程闭环 | mmaction2-overview + model-onboarding + 2026-07-13 计划 |
| 5 | live-module.md | Live 模块 | 落地后架构与关键决策 | 两篇 live plan |
| 6 | architecture.md | 系统架构 | 完整结构总览 + 五阶段详解（定位/跟随/动作/身份/应用）+ 末节进度与未来计划 | openspec 总管/各子 change design + tasks |
| 7 | identity-and-retrieval.md | 身份标识与检索 | 定位追踪+猫 Re-ID+RAG 式物体标识三件事的整合专篇（对比学习作统一视角） | registry-retrieval + 总管/子 change design + 猫定位检测实操资料 |
| 8 | identity-tokenizer.md | 身份-动作 Tokenizer（专篇） | 重点结构独立成篇：FLOAT×TiTok 架构/两阶段路线/对比学习目标/评测矩阵 | identity-action-tokenizer change 全文 |
| 9 | lessons.md | 研究结论与踩坑 | 关键点五大问题/标注体系教训/用户裁定时间线 | keypoint-extraction-pitfalls + change 裁决记录 |
| 10 | third-party-notes.md | 第三方项目借鉴 | 每个项目八节模板（D5） | 两篇 third-party 文档 |
| 11 | handover-guide.md | 交接与协作指南 | 新协作者上手入口 | 新写（D7） |

### D3 逐篇去留决策表（删除的唯一依据）

| 现有文档 | 评估 | 处置 | 信息去向 |
|---|---|---|---|
| mmaction2-overview.md | 活跃参考 | 吸收后删 | 模型族详解→3，训练链路/四模式→4 |
| model-onboarding.md | 活跃参考（9-16 仍更新） | 吸收后删 | registry/checkpoint/接入→3、4 |
| detection-annotation-taxonomy.md | 活跃参考 | 吸收后删 | 全文→2 |
| live-page-integration-plan.md | 已落地 | 吸收后删 | →5 |
| live-realtime-inference-plan.md | 已落地 | 吸收后删 | →5 |
| keypoint-extraction-pitfalls.md | 活跃研究结论 | 吸收后删 | 全文→9 |
| third-party-pet-videos.md | 借鉴笔记 | 吸收后删 | →10 |
| third-party-remix-petra.md | 借鉴笔记 | 吸收后删 | →10 |
| tasks.md（wiki） | 过时 | 直接删 | 3.2 核对无独有信息后弃 |
| docs/plans/2026-07-13-….md | 已落地 | 吸收后删 | →4 历史决策节 |
| docs/plans/2026-08-15-phase2-….md | 部分过时 | 吸收后删 | →6 |
| docs/宠物动作识别研究计划.docx | 二进制 | **保留原位** | 仅在 1 中登记 |
| README.md | 过时 | **重写** | 模块总览+指向 1 |
| 各子目录 README | 有效 | 保留不动 | — |

### D4 每篇内容规格（逐节 outline，写作时的验收标准）

#### 4.1 repo-inventory.md《仓库资产盘点》

- **头部**：盘点基准日 2026-09-16；位置图例（🗄️仓库内 / 🖥️pet 远程 / 💽NAS）；导航表（2–11 号文档一览，各一句话）
- **§1 数据资产表**（列：资产/路径/规模/位置/状态/用途）逐项收录：datasets/cats（552MB、8 zip、两批双人标注）；quadruped_action（占位骨架）；data/papers.db（239 篇 / 519 类目）；extracted_papers.json、researched_papers.json（frontier）、researched_papers_identity.json（livestock/身份）、papers.db.bak-seed；results/live/live.db（1 源 / 1 截屏）；💽NAS UCF101 13320 段；🖥️pet checkpoints 与 ~/results/batch/
- **§2 产物资产表**：results/ 九个子目录（training/speedrun/batch/gate*4/skeleton/live）
- **§3 代码模块**：server 8 路由一句话；scripts 27 个按用途分组；petlib 7 模块；web 28 页面按 7 组；configs 11 文件；models/mmaction2 vendored
- **§4 论文模块现状**
- **§5 项目管理数据**：management/ 七子目录文件数
- **§6 openspec 一览**：8 活跃表（名称/一句话定位/进度 x/y/状态/所属类别）+ 16 归档列表，详情见 6 号 §8，身份细节指 7/8
- **§7 外部资产索引**：pet、NAS、third-party/ 5 库
- **附录 A**：顶层散落文件清单 → 指向清理 change；**附录 B**：空/失效目录

#### 4.2 datasets.md《数据集全景》

- §1 总览表
- §2 cats v1（552MB、蒋/崔双人标注、~3h、activity 伞类问题）
- §3 pet_action_mammal_v0（七类、~3h、迁移基线、1.13 V-JEPA 对照）
- §4 UCF101（NAS、13320/101 类、tokenizer 阶段 A 验证）
- §5 34 段白天事件片段（**14.7 分钟语料事实**、三率、3 告警结案）
- §6 kinetics400（仅烟测）
- §7 quadruped_action 占位
- §8 标注类目规范全文（detection-annotation-taxonomy **全文迁入**）
- §9 label_map / ann_file 约定

#### 4.3 models.md《模型》（以模型为条目：简介 + 实测结果两段式）

- §1 重要模型总览表
- §2 分类模型逐个条目（两段式）：videomaev2-base×2 error、slowonly-resnet50、tsm-resnet50、timesformer-divst、tsn-resnet50（k400 烟测全套指标）
- §3 关键点模型条目：HRNet / ResNet-101 / SuperAnimal（裁剪裁定）
- §4 检测模型条目：GroundingDINO / YOLO11 / OWLv2（撤下裁定）
- §5 注册库其余模型速览：26 个 registry 全表，**未实测项明确标注**
- §6 结论汇总表（D6 四要素）

#### 4.4 training-guide.md《训练体系》

- mmaction2 机制、四种训练模式、registry/configs/hooks、远程闭环
- 历史决策回顾（2026-07-13 计划）

#### 4.5 live-module.md《Live 模块》

- 落地架构（表/stream_token/SSE 管线）+ 关键决策
- 与 pet-videos 借鉴映射（指向 10 号）

#### 4.6 architecture.md《系统架构》（完整结构 + 逐阶段索引 + 进度）

- **§0 术语表**（D8 风格准则首次定义要求；本文档用到的术语一张表收齐）：
  - mmaction2（动作识别框架）、GroundingDINO（开放词汇检测器，可用文字提示找物体）、DINOv2（自监督视觉特征提取器，把图片变向量）、FAISS（向量相似度检索库）、SAM（按提示分割任意物体的模型）、OWLv2（开放词汇检测器）、HDBSCAN（基于密度的聚类算法）、ByteTrack（多目标跟踪算法）、CatHuBERT（伪标签迭代预训练范式，迭代地给行为打伪码并预训练下游编码器）、FLOAT（身份-动作解耦的视频生成方法）、TiTok（视觉 tokenizer，用几十个 token 表达一张图）、checkpoint（训练好的模型权重文件）、NAS（网络存储，本项目指挂载在开发机上的共享磁盘）、RTF（实时率，推断速度指标）
  - **对比学习（contrastive learning）**：核心思想——把"同一类"样本在特征空间里拉近、把"不同类"样本推远的学习方式。训练时构造正样本对（positive pair，如同一只猫的两帧）和负样本对（negative pair，如两只不同猫的同帧），优化"正对相似度最大化、负对相似度最小化"的目标。本项目中身份标识的核心视角就是对比学习：**同一只猫应该共享同一组身份 tokens（positive invariance），不同猫应该有不同的身份 tokens（negative discrimination）**——猫 Re-ID（DINOv2+FAISS）和身份-动作 Tokenizer 的 track 级 InfoNCE 都是这个原理的不同实现。
- **§1 完整结构总览**：一张表把整条管线说清——监控视频 → ① 定位与跟踪 → ② 跟随视角生成 → ③ 动作表征 → ④ 身份识别与提取 → ⑤ 应用出口；每阶段一行：输入/输出/算法/代码落点/对应 change 与决策 ID；深入内容指向 7/8
- **§2 定位与跟踪**：一句话指向 7 号 §1；理由：ByteTrack 全帧率否决（D1）、GatedTracker 否决（D1b）、关键点降级辅助信号（D2）
- **§3 跟随视角生成**：follow_adaptive 512² H.264 + 尺寸离群过滤 + 沙发漂移渲染层过滤
- **§4 动作表征（识别动作）**：窗口特征四候选选型 + UMAP+HDBSCAN 行为簇 + 路线 W CatHuBERT + 四闸门；为什么零训练优先、为什么无监督发现
- **§5 身份识别与提取（只讲索引）**：两条路线各一句——① 检索式（猫 Re-ID + 物体实例识别，以**对比学习**为统一视角：**同猫跨时间/视角共享身份**，**不同猫互不混淆**，详见 7 号）；② 身份-动作解耦 Tokenizer（用对比损失保证身份一致性，详见 8 号）。对比学习是统一两路线的概念性视角。
- **§6 应用出口**：spot-check-cli 抽查报告、behavior-anomaly-detection
- **§7 跨切面**：plf/pet_tokenizer 双环境、petlib 可替换架构、D1–D9 决策索引
- **§8 当前进度与未来计划**：四分类表 + 闸门里程碑 + 二期 P0–P2 对照

#### 4.7 identity-and-retrieval.md《身份标识与检索》（定位追踪+猫 Re-ID+RAG 式物体标识三件事的整合专篇）

用户口径："定位、追踪宠物；识别宠物身份；参考RAG，对物体进行身份标识"。本篇用最通俗的语言把三件事一次讲清。**全文执行 D8 老师腔准则；以对比学习为统一视角——同一只猫在不同时间/视角应该共享同一身份（positive invariance），不同猫应该互相区分（negative discrimination）——把这条原理在三件事里反复对照说明**，便于读者抓住共同主线。

- **§0 一句话概览**：身份标识 = 知道"视频里这只猫是谁、这个碗是哪个猫的、那个摄像头是不是上次那个"；三层——定位追踪 / 个体身份 / 物体实例
- **§1 宠物定位与跟踪**：GDINO 文字提示 → 多 prompt 抽样+插值平滑 → 运动校正 v5（off-alpha 0.6 等）；**为什么**：ByteTrack 否决、关键点降级；代码 `scripts/pet_detect_track.py`、产物 `results/batch/*/track.json`；34/34 完成、检出率 0.939、3 告警结案
- **§2 跟随视角生成**：512×512 以猫为中心裁剪 + follow_adaptive + 沙发漂移渲染层过滤
- **§3 猫个体识别（猫 Re-ID）**：
  - 什么时候需要：多机位/多时段区分"这两只是同一只 vs 另一只"
  - 原理（人话）：给每只猫拍几张"身份照"→ DINOv2 提特征（成向量）→ 存进 FAISS；新猫帧也提一串数字去库里找最像的，相似度超阈值就算"同一只"；未登记个体标"未知猫 #N"
  - **对比学习视角**：Re-ID 就是这个原理的检索实现——同猫跨时间/视角特征应当相似（positive）、不同猫特征应当区分（negative）。同一只猫走路、睡觉、跑酷的三段视频帧，提取的特征应该聚到一起；两只不同猫在同一个沙发上，特征应该分开。FAISS 的相似度检索就是这个性质的工程实现。
  - 代码 `scripts/register_cats.py`、spot-check-cli 的猫个体档案字段
  - 与 8 号身份-动作 Tokenizer 的区别：Re-ID 仅判"谁是谁"；Tokenizer 还要解耦"身份与动作"用于重建/生成
- **§4 RAG 式物体实例标识**：名字里的"RAG"是类比思路（检索增强）——不靠模型直接说"这个碗是A碗"，而是**预先把每个物体"登记入库"**，新帧去库里检索最像的那个
  - 流程：① SAM 对固定机位一次性分割所有候选物体 ② DINOv2 提特征存库 ③ 帧差变更触发重分割 ④ 新帧中的物体提特征检索库判定是否同一个；OWLv2 图像引导对照、GDINO 文本提示备档（碗/摄像头曾被裁定撤下）
  - **对比学习视角**：和猫 Re-ID 同理——同一个物体跨时间/视角/光照应当特征相似（positive），不同物体应当区分（negative）。同一个碗放在厨房、客厅、被人端着走，提取的特征应该聚到一起；碗 vs 砂盆 vs 摄像头 应可分辨。
- **§5 统一登记-检索抽象（D9）**：猫与物体走同一套抽象——登记照 / 嵌入库 / FAISS 索引 / 检索阈值 / 未登记标记位；代码一套两业务复用
- **§6 数据资产**：登记照库位置、嵌入向量库位置、配置 schema（petlib/registry.py）；与 1 号交叉引用
- **§7 未决与依赖**：器物边界、检索阈值调参、多猫 ID 切换；与 4 号训练、5 号 Live、11 号交接交叉引用

#### 4.8 identity-tokenizer.md《身份-动作 Tokenizer（专篇）》

重点结构单独成篇，全部取自 identity-action-tokenizer change。**全文贯穿对比学习视角——身份一致性是这个架构的核心目标之一**。

- **§1 问题与定位**：可控行为潜空间；猫语料太少（34 段=14.7 分钟+3k clips）→ 先在 UCF101（13320 段）验证再迁移
- **§2 架构设计**（用户定义 2026-09-16，FLOAT×TiTok 杂交）：
  - ① 几十个跨时间共享身份 tokens（K_id=32）= "这是哪只猫"——**这就是对比学习视角在架构上的体现：身份 tokens 在时间维度上强制共享，是在把"同猫跨时间"的 positive invariance 写进模型结构里**
  - ② 每帧一个动作 latent（z_t 32d）= "这帧在动什么"
  - ③ 轻量解码器以（身份+动作）重建视频——重建成立则解耦成立
- **§3 两阶段路线**：
  - **阶段 A UCF101**（重建+动作 CE+类别弱监督；token 数缩放 8/16/32）
    - **中期检查点**（z_t 探针 top1@101 类 + 身份 dropout/交换消融）
    - 身份一致性验证：训练后取不同人的帧看身份 tokens 是否聚类正确——同一人跨帧聚一起，不同人分开
  - **阶段 B 猫语料迁移**（mammal_v0 + cats v1 + followcam）
    - **track 级 InfoNCE 对比损失**：构造 positive pair = 同一只猫的两段视频帧 / 同一只猫相邻帧；negative pair = 不同猫的同帧 / 不同猫跨帧——优化"正对相似度↑、负对相似度↓"。这就是把对比学习视角落进损失函数。
    - 跨猫交换重建（消融：把 A 猫的帧用 B 猫的身份 tokens 重建，看是否被识别为非 A）
- **§4 评测矩阵**（design T-A4 全表）：重建质量 / 动作探针（5 类）/ **身份检索（同猫 vs 不同猫的检索精度）** / **身份泄漏（动作探针是否被身份信号污染）** / **交换重建（跨身份重建是否被识别）**——评测维度全面围绕"对比学习视角下的同/异身份分辨力"
- **§5 训练配方笔记**：TiTok/AdapTok/1d-tokenizer/FLOAT 的 mask 策略、解码器规模、LR/epoch；身份 InfoNCE 温度/负样本数等超参
- **§6 验收裁定与回流**：CatHuBERT 骨干是否采用本 tokenizer（**用户验收**）→ 产出回流 video-feature-latent 任务 1.7
- **§7 环境与依赖**：pet_tokenizer（transformers≥4.55）、NAS UCF101 manifest、V-JEPA 2 fpc16

#### 4.9 lessons.md《研究结论与踩坑》

- 关键点提取五大问题全文、K400 经验共性、复活条件分析（**原文保留**）
- **用户裁定时间线表**（含运动校正 v5 参数）
- 标注表不可靠教训（activity 伞类占一半 → 无监督发现行为的原始动机）

#### 4.10 / 4.11 → 见 D5、D7

### D5 第三方借鉴文档内容规格（10 号 third-party-notes.md）

覆盖 `third-party/` 5 个库，分两种深度：重点项目（pet-videos、remix-petra）用八节模板，调研型（kabr-tools、keypoint-moseq、PigDetect）用轻量条目（是什么/为何引入/是否已用上/处置建议）。

**八节模板（重点项目）**：

1. 定位与来源：是什么、从哪来、为何留在本仓库、版本/commit pin 状态
2. 技术栈与架构速览
3. 目录导览：关键文件/页面/模块清单
4. 我们借鉴了什么：具体到模块/交互/代码片段级，并**映射到本仓库落地点**（pet-videos → Live 模块源管理与播放器形态；remix-petra → 前端 UI 风格、宠物档案字段、AI 日报思路、Gemini API 现状）
5. 明确不学/反模式（含原因）
6. 本地运行方式：如何跑起来看效果
7. 同步策略：vendored 只读还是可改、上游更新怎么办
8. 交叉引用：相关 wiki 篇目/skill/change

### D6 结论与关键数据登记规范

训练/测试结论、重要数据在 3/6/7/8 号文档中出现时必须带**四要素**：①日期 ②来源（change 任务号或实验名）③关键数字 ④证据路径（results/… 或 data/…）。

写作时必须核对收录的已知重要数据起点（不完全清单）：
- k400 烟测全套指标（§4.3）
- 34 段批处理三率 + 3 告警段结案（§4.2/4.9）
- 语料事实修正：34 段 = 14.7 分钟（§4.2）
- 关键点 MC 实测：mean_conf 0.367 / >0.5 帧 0.2%（§4.3/4.9）
- 检测裁定：碗全误框、camera 召回 4/1859（§4.3）
- 运动校正 v5 参数与实测（触发 12.0%/偏移 max 108px/锚点像素级一致）（§4.9）
- 5 个训练 run 状态（含 error）（§4.3）
- 身份一致性：track 级 InfoNCE 在 stage B 验证（§4.8）

### D7 交接与协作指南（11 号 handover-guide.md）的定位与安全边界

面向**新协作者**的单一上手入口，与 1 号盘点（有什么）互补，六节结构：

1. 项目速览与当前阶段：进度快照（活跃 change、任务看板 `management/projects/*/tasks.json`、11 月中期验收 KPI）
2. 环境搭建：本地一键启动（`start_services.sh`，3000/8788）、pet/A100、NAS——**只写"去哪找"**，不复制凭证
3. 工作纪律：三阶段 OpenSpec 流程、远程只读执行/git push 同步、GPU 共享——引用 AGENTS.md 与 remote-server-discipline skill
4. 协作约定：git 提交规范、11 篇 wiki 维护责任、任务看板与报表
5. FAQ：服务起不来/连不上 pet/训练报错的排查入口
6. 安全红线：不提交密钥、不在本地跑 GPU、不直接改远程

### D8 写作风格准则（适用全部 11 篇）

**基调 = 交接文档风格**——本套文档是给项目协作者、新接手者、未来的你和 AI 看的入口，目标"读一遍能上手、卡住时知道去哪查"。执行六条：

1. **老师腔**：用说人话的方式讲，每段先点目的（"为什么有这一步""这节要解决什么问题"），再讲方法，最后给坑/未定项；避免论文摘要腔与营销稿腔
2. **术语首次出现必须定义**：任何专业名词（mmaction2、DINOv2、FAISS、SAM、HDBSCAN、CatHuBERT、FLOAT、TiTok、checkpoint、RTF、ByteTrack、OC-SORT、GroundingDINO、OWLv2、**对比学习**等）首次出现用"X（…）"括注或紧跟一句通俗定义；同一篇内不重复定义
3. **架构文档必带术语表**：6 号 architecture 在 §0 用一张表集中定义本文档用到的全部术语
4. **类比与示例**：抽象概念配生活类比（如"RAG 式检索 = 把每个碗拍张照片存进抽屉，新看到一只碗就去抽屉里找最像的"）或代码/路径示例
5. **避免**：缩写堆叠（一句里连续三个未定义缩写）、长定语从句、"显然/显然可以"之类的不解释、黑话俚语；该用专有名词时先用人话讲一遍再用专有名词
6. **风格可在 11 号交接指南加"读者画像"章节固化**：新人/AI Agent/未来自己

### D9 删除的执行顺序与回滚

整合 → 逐节核对 D3 决策表 → **删除动作单独 git commit**，绝不与新增混——误删可单点 revert。

## Risks / Trade-offs

- [整合走样丢细节] → D4 逐节规格即验收标准；tasks 含逐节对照核对；git 历史兜底
- [结论数字抄错] → D6 四要素 + 与 json 原文逐条核对
- [wiki 排序混乱] → id 1–11；现存无 id 文档自然排后
- [live 两篇 plan 中间讨论被丢弃] → 只保留落地现状+关键决策，review 时可补
- [盘点/进度很快过时] → 头部标注基准日；进度日常指向任务看板
- [交接文档泄露敏感信息] → D7 安全边界：凭证只写"去哪找"
- [对比学习视角只在 6/7/8 号强调、未推到全部 11 篇] → D8 §2 要求术语首次出现必定义，覆盖全局

## Migration Plan

1. 按 D4–D8 规格写 11 篇新文档（id 1–11）
2. 逐节核对 D3 决策表：11 篇待删文档的信息均有落点
3. `git rm` 被吸收文档，独立 commit
4. 重写 README.md，独立 commit
5. web Wiki 页人工验证

回滚：git revert 对应 commit，无数据/代码耦合。

## Open Questions

（无——live 计划"不保留计划体例"、docx 保留原位为已定决策；身份一致性原理写入 6/7/8 号三篇并以对比学习为统一视角为已定设计；异议可在 review 提出。）