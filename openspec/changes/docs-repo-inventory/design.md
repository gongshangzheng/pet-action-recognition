# Design: docs-repo-inventory

## Context

文档现状（2026-09-16 盘点）：

| 位置 | 文件 | 状态 |
|---|---|---|
| `management/docs/`（wiki，9 篇） | mmaction2-overview(183行)、model-onboarding(145行)、keypoint-extraction-pitfalls(142行)、third-party-remix-petra(131行)、live-realtime-inference-plan(118行)、live-page-integration-plan(115行)、detection-annotation-taxonomy(98行)、third-party-pet-videos(108行)、tasks(30行) | 多数活跃；live 两篇已落地；tasks.md 停在 7 月 |
| `docs/plans/`（2 篇） | 2026-07-13 mmaction2 训练集成计划、2026-08-15 二期研究计划 | 前者已落地；后者部分过时（P0 已完成大半） |
| `docs/` | 宠物动作识别研究计划.docx（二进制） | 保留 |
| 根目录 | README.md（118 行） | 缺 training/live/speedrun/pipeline 等半数模块说明 |
| 各子目录 | datasets/quadruped_action/README.md、management/README.md、templates/README.md 等 | 有效的目录级说明，保留不动 |

Wiki 机制（`server/routers/management.py`）：递归扫描 `management/docs/**/*.md`，解析 YAML frontmatter（title/author/date/tags/summary/id），slug=文件名（限 `^[a-zA-Z0-9_/-]+$`），按数字 id 升序、无 id 者按日期倒序排后。现存 9 篇均无 id 字段。

与现有知识库的分工：`.claude/skills/`（15 个）是 agent 操作指南、`AGENTS.md` 是 agent 仓库纪律、wiki 是**人读的项目知识沉淀**——三者不互相复制内容，wiki 用链接引用 skills。

## Goals / Non-Goals

**Goals**
- 一份《仓库资产盘点》作为全库唯一入口，回答"有什么重要内容/数据、在哪、什么状态"
- 一套主题统一、带 frontmatter、id 有序的 wiki 文档（7 篇），吸收全部现存文档的有效信息
- 每篇被删/被吸收文档有明确的"信息去向"记录，重要信息零丢失

**Non-Goals**
- 不清理顶层散落文件（CanvasPlayer.vue、live.py、pet-videos.zip 等）——仅在盘点文档登记为"待清理项"，清理另立 change
- 不改任何代码、数据库、数据集、results 产物
- 不动 `.claude/skills/`、`AGENTS.md`、`openspec/`（change 体系自洽，roadmap 文档只做索引）
- 不整理 management/ 下的日报/周报/会议等结构化业务数据（那是项目管理模块的数据，不是文档）

## Decisions

### D1 文档集落位与命名

统一放 `management/docs/`（web Wiki 页自动可见，无需改代码）。文件名 ASCII kebab-case（slug 正则限制），frontmatter 必带 `id: 1..7` 使新文档排在 wiki 列表最前（现存无 id 文档排后）。

**备选**：放 `docs/`——否，`docs/` 无 web 入口且已沦为 plans 堆放处（本次清空后仅留 docx）；每主题拆目录——否，9→7 篇规模平铺即可。

### D2 目标文档集（7 篇）与内容来源映射

| id | 文件 | 标题 | 内容来源（全量整合） |
|---|---|---|---|
| 1 | repo-inventory.md | 仓库资产盘点 | 新写（本次盘点素材）+ 指向 2–7 的索引 |
| 2 | training-guide.md | 训练体系：mmaction2 与模型接入 | mmaction2-overview + model-onboarding + 2026-07-13 计划的落地决策回顾 |
| 3 | data-and-annotation.md | 数据集与标注规范 | detection-annotation-taxonomy + 数据集现状（cats 552M 两批标注、quadruped 占位、NAS UCF101） |
| 4 | live-module.md | Live 模块：架构与实时推理 | live-page-integration-plan + live-realtime-inference-plan 的**落地后现状**与关键设计决策 |
| 5 | research-notes.md | 研究结论与踩坑记录 | keypoint-extraction-pitfalls（保留 8-15 复活条件分析）+ K400 标注体系共性经验 |
| 6 | third-party-notes.md | 第三方项目借鉴 | third-party-pet-videos + third-party-remix-petra 合并，"可借鉴/反模式"两节保留 |
| 7 | research-roadmap.md | 研究路线与 change 全景 | 2026-08-15 二期计划（KPI/路线+现状对照）+ openspec 8 活跃/16 归档 change 索引 |

每篇新文档头部列"来源文档"清单；整合非逐字复制，但**结论、数据、决策、坑、路径、命令必须保留**，计划体例（阶段拆分/执行顺序/风险清单）在对应工作已落地后不保留。

### D3 逐篇去留决策表（删除的唯一依据）

| 现有文档 | 评估 | 处置 | 信息去向 |
|---|---|---|---|
| mmaction2-overview.md | 活跃参考 | 吸收后删 | → 2 |
| model-onboarding.md | 活跃参考（9-16 仍更新） | 吸收后删 | → 2 |
| detection-annotation-taxonomy.md | 活跃参考 | 吸收后删 | → 3 |
| live-page-integration-plan.md | 已落地（Live 页已上线） | 吸收后删 | → 4 |
| live-realtime-inference-plan.md | 已落地（SSE 推理已上线） | 吸收后删 | → 4 |
| keypoint-extraction-pitfalls.md | 活跃研究结论（9-16 仍更新） | 吸收后删 | → 5 |
| third-party-pet-videos.md | 借鉴笔记 | 吸收后删 | → 6 |
| third-party-remix-petra.md | 借鉴笔记 | 吸收后删 | → 6 |
| tasks.md（wiki） | 过时（7-17 后未动，任务已迁移 projects/*/tasks.json） | 直接删 | 核对无独有信息后弃 |
| docs/plans/2026-07-13-….md | 已落地 | 吸收后删 | → 2 历史决策节 |
| docs/plans/2026-08-15-phase2-….md | 部分过时 | 吸收后删 | → 7（含"计划 vs 现状"对照） |
| docs/宠物动作识别研究计划.docx | 二进制 | **保留原位** | 仅在 1 中登记路径+摘要 |
| README.md | 过时 | **重写** | 模块总览+指向 1 |
| 各子目录 README（quadruped_action、management、templates 等） | 有效 | 保留不动 | — |

### D4 盘点文档（1）的资产范围与位置标注

六类资产，每项标注三级位置：**仓库内**（相对路径+规模）/ **远程 pet**（如 `~/pet-action-recognition/checkpoints/…`，只登记已知路径，不 ssh 核实——保持本 change 纯本地）/ **NAS**（如 UCF101 13320 段）：

1. **数据**：datasets/cats（552MB，蒋/崔两批标注 zip）、datasets/quadruped_action（占位骨架+3 个 ann list）、NAS UCF101、data/（papers.db 239 篇+519 类目、extracted_papers.json、researched_papers.json、researched_papers_identity.json）
2. **训练/评测产物**：results/training（metrics.json、test_results.json k400 烟测 top1=0.77、5 个 work_dirs）、results/speedrun（results.json）、results/batch（34 段白天批处理+batch_report.md+告警 3 段）、results/gate0a/0b/4（检测/跟踪验收门）、results/skeleton（ap10k/dlc 可视化）、results/live（live.db）
3. **代码**：server 8 路由、scripts 27 个（按推理/训练/批处理/关键点分组）、petlib、web 28 页面、configs 11 个、models/mmaction2（vendored 只读）
4. **论文模块**：DB 统计+两类 research JSON
5. **项目管理数据**：management/ 各子目录文件数统计
6. **openspec**：8 活跃+16 归档一览（一句话状态，详细见 7）
附录：顶层散落文件登记为"待清理项"（另行 change）。

### D5 删除的执行顺序与回滚

整合 → 逐节核对决策表 → **删除动作单独一个 git commit**（`docs: remove docs absorbed into unified wiki`），先于或同批于整合 commit 之后均可，但绝不与新增混在一个 commit——任何误删可单点 revert。

## Risks / Trade-offs

- [整合走样丢细节] → 每篇新文档列来源清单；tasks 含"逐节对照来源核对"步骤；git 历史兜底
- [wiki 列表排序混乱] → 新文档统一 id 1–7；现存无 id 文档自然排后，不改后端
- [live 两篇 plan 的中间讨论被丢弃] → 决策（D2）已明确只保留落地现状+关键决策；用户可在 review 新文档时补充
- [盘点数据很快过时] → 1 号文档头部标注"盘点基准日 2026-09-16"；roadmap 的 change 状态标注截止日

## Migration Plan

1. 写 7 篇新文档（id 1–7，frontmatter 齐全）
2. 核对 D3 决策表：每篇待删文档的信息都能在新文档找到落点
3. `git rm` 11 篇（9 wiki 中 8 篇被吸收 + tasks.md；docs/plans/ 2 篇），单独 commit
4. 重写 README.md，单独 commit
5. 打开 web Wiki 页人工验证：7 篇排序正确、旧文档消失、docx 仍可从盘点文档索引

回滚：git revert 对应 commit 即可，无数据/代码耦合。

## Open Questions

（无——D3 中 live 计划"不保留计划体例"、docx 保留原位两项为已定决策，如用户有异议在 review 时提出即可，不影响整体结构。）
