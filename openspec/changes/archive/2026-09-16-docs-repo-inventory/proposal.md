# Proposal: docs-repo-inventory

## Why

仓库运行三个月积累了大量资产——数据集（cats 552MB、quadruped、UCF101 on NAS）、论文库（papers.db 239 篇）、训练/评测/批处理产物（results/ 全系）、8 个活跃 openspec change——但文档散落三处（`management/docs/` 9 篇 wiki、`docs/plans/` 2 篇计划、根 `README.md`），且部分已过时：README 缺 training/live/speedrun 等半数模块的说明；`management/docs/tasks.md` 停在 7 月（已被项目树 tasks.json 任务看板取代）；两篇 live plan 已落地实施。没有单一入口能回答"这个库里有什么重要的内容和数据"。同时项目即将进入**多人协作/交接阶段**：其他使用者需要能凭文档自主完成环境搭建、远程训练、日常工作与进度衔接，而不是依赖口口相传。需要：① 盘点全部重要内容与数据，落成一份资产盘点主文档；② 把散落的旧文档统一成一套，该删的删、该整合的整合——**删除仅限已过时或已被取代的文档，重要信息必须先整合保留**；③ 补齐交接与协作指南，使文档集同时成为新人上手与工作交接的完整交接包。

## What Changes

- **新增资产盘点主文档**（`management/docs/repo-inventory.md`）：作为全库唯一入口，盘点六类资产——数据资产（datasets/、data/、NAS、远程 pet 服务器）、训练/评测产物（results/training、speedrun、batch、gate0a/0b/4、skeleton、live）、代码模块（server 8 路由、scripts 27 个、petlib、web 28 页面、configs 11 个）、论文模块、项目管理数据、openspec change 全景（8 活跃 + 16 归档）。
- **文档整合统一**：9 篇 wiki + 2 篇 plans 按主题归并为一套编号文档（11 篇，id 1–11）：仓库资产盘点 / 数据集全景 / 模型 / 训练体系 / Live 模块 / 系统架构 / 身份标识与检索 / 身份-动作 Tokenizer 专篇 / 研究结论与踩坑 / 第三方借鉴 / 交接与协作指南，全部带 frontmatter。
- **新增《系统架构》文档**：完整结构一次讲清——宠物定位与跟踪 → 跟随视角生成 → 动作表征 → 身份识别与提取 → 应用出口，五阶段逐个详解；末节并入**当前进度与未来计划四分类**（主线执行序 / 条件启动含触发条件 / 研究型 / 已归档）+ 闸门里程碑与二期 P0–P2 对照（避免与架构重复）；§0 带术语表。
- **新增《身份标识与检索》整合专篇**（7 号）：把“定位追踪宠物 + 识别宠物身份 + 参考RAG 对物体进行身份标识”三件事用一篇文章讲完，**以对比学习为统一视角**——同一只猫在不同时间/视角应共享同一身份（positive invariance）、不同猫应互相区分（negative discrimination）；这一原理贯穿猫 Re-ID、物体实例识别与身份-动作 Tokenizer 三条路线，便于读者抓住主线。
- **重点结构单独成篇**：《身份-动作 Tokenizer（专篇）》详述 FLOAT×TiTok 解耦架构（身份 tokens K_id=32 + 逐帧动作 latent + 重建验证）、UCF101→猫两阶段路线、评测矩阵与验收裁定；track 级 InfoNCE 对比损失是身份一致性的损失函数表达。
- **全套写作风格 = 交接文档 / 老师腔**（D8）：术语首次出现必须给定义；架构文档带术语表；类比与示例优先；不堆黑话；适用全部 11 篇。
- **新增三篇事实型文档**（内容取自 results/ 产物与 openspec change 实录，非泛泛综述）：
  - 《数据集全景》：当前所有数据集——cats v1（552MB 蒋/崔两批标注）、pet_action_mammal_v0（七类 ~3h）、NAS UCF101（13320 段）、quadruped_action（占位）、34 段白天事件片段（总素材仅 14.7 分钟的语料事实）、kinetics400（烟测）——各自的来源/规模/结构/label_map/位置/状态/用途，并全文迁入标注类目规范。
  - 《模型》：**重要模型逐个条目，每个固定两段式——简介 + 实测结果**：分类模型（videomaev2×2 error、slowonly/tsm/timesformer 各 1 run、tsn-resnet50 k400 烟测 top1 0.77）、关键点模型（HRNet/ResNet-101/SuperAnimal 及裁剪裁定）、检测模型（GroundingDINO/YOLO11/OWLv2 及撤下裁定）；registry 其余未实测模型明确标注。
  - 训练/测试结论与重要数据按 design D6 四要素登记：日期/来源/关键数字/证据路径。
- **删除过时文档**（共 4 篇，关键信息先整合）：
  - `management/docs/tasks.md`（30 行，7 月后未更新，任务管理已迁移到 `management/projects/*/tasks.json`）
  - `docs/plans/2026-07-13-mmaction2-training-integration-plan.md`（已落地：training 模块 + registry 已上线，落地后决策回放进训练体系文档）
  - `docs/plans/2026-08-15-phase2-research-plan.md`（内容整合进系统架构文档 §8 后删除）
  - 旧 wiki 中被新文档完全吸收的对应文件（live 两篇 plan、mmaction2-overview 等整合后原文件删除，详见 design 的逐篇去留决策表）
- **新增交接与协作指南**（`management/docs/handover-guide.md`，11 号）：面向新协作者的单一上手入口——环境搭建（本地服务/远程 pet 与 A100/NAS）、工作纪律（三阶段 OpenSpec 流程、远程服务器纪律、GPU 共享）、当前进度快照（活跃 change/任务看板/里程碑）、协作约定（git 规范、文档维护责任）、安全红线（不写密钥、不在本地跑 GPU 任务）。
- **重写根 `README.md`**：反映当前 8 大模块（papers/training/evaluation/speedrun/live/management/datasets/pipeline）与文档入口。
- **保留保证**：每篇被删文档在 design 决策表中列出"信息去向"；删除动作在 tasks 中置于整合完成并核对之后。

## Capabilities

### New Capabilities

（无——纯文档变更，不引入系统能力）

### Modified Capabilities

（无——不改任何代码行为、API、数据）

> 本 change 为纯文档整理（docs-only），在 `.openspec.yaml` 声明 `skip_specs: true`。

## Impact

- **文件**：`management/docs/`（新增 11 篇、删除被吸收的旧篇）、`docs/plans/`（清空）、`README.md`（重写）、`datasets/quadruped_action/README.md`（保留不动）
- **Web Wiki 页面**：management 路由递归扫描 `management/docs/`，文件增删自动反映到前端导航，无需改代码
- **不受影响**：所有代码、数据库、数据集、results 产物、`.claude/skills/`（agent 操作指南，与 wiki 分工见 design）、AGENTS.md（agent 专用，保留独立维护）
