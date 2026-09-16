# Proposal: docs-repo-inventory

## Why

仓库运行三个月积累了大量资产——数据集（cats 552MB、quadruped、UCF101 on NAS）、论文库（papers.db 239 篇）、训练/评测/批处理产物（results/ 全系）、8 个活跃 openspec change——但文档散落三处（`management/docs/` 9 篇 wiki、`docs/plans/` 2 篇计划、根 `README.md`），且部分已过时：README 缺 training/live/speedrun 等半数模块的说明；`management/docs/tasks.md` 停在 7 月（已被项目树 tasks.json 任务看板取代）；两篇 live plan 已落地实施。没有单一入口能回答"这个库里有什么重要的内容和数据"。需要：① 盘点全部重要内容与数据，落成一份资产盘点主文档；② 把散落的旧文档统一成一套，该删的删、该整合的整合——**删除仅限已过时或已被取代的文档，重要信息必须先整合保留**。

## What Changes

- **新增资产盘点主文档**（`management/docs/repo-inventory.md`）：作为全库唯一入口，盘点六类资产——数据资产（datasets/、data/、NAS、远程 pet 服务器）、训练/评测产物（results/training、speedrun、batch、gate0a/0b/4、skeleton、live）、代码模块（server 8 路由、scripts 27 个、petlib、web 28 页面、configs 11 个）、论文模块、项目管理数据、openspec change 全景（8 活跃 + 16 归档）。
- **文档整合统一**：9 篇 wiki + 2 篇 plans 按主题归并为一套编号文档（训练体系 / 数据与标注 / Live 模块 / 研究结论与坑 / 第三方借鉴 / 研究路线），全部带 frontmatter（title/date/id/tags/summary）。
- **删除过时文档**（共 4 篇，关键信息先整合）：
  - `management/docs/tasks.md`（30 行，7 月后未更新，任务管理已迁移到 `management/projects/*/tasks.json`）
  - `docs/plans/2026-07-13-mmaction2-training-integration-plan.md`（已落地：training 模块 + registry 已上线，落地后决策回放进训练体系文档）
  - `docs/plans/2026-08-15-phase2-research-plan.md`（内容整合进研究路线文档后删除）
  - 旧 wiki 中被新文档完全吸收的对应文件（live 两篇 plan、mmaction2-overview 等整合后原文件删除，详见 design 的逐篇去留决策表）
- **重写根 `README.md`**：反映当前 8 大模块（papers/training/evaluation/speedrun/live/management/datasets/pipeline）与文档入口。
- **保留保证**：每篇被删文档在 design 决策表中列出"信息去向"；删除动作在 tasks 中置于整合完成并核对之后。

## Capabilities

### New Capabilities

（无——纯文档变更，不引入系统能力）

### Modified Capabilities

（无——不改任何代码行为、API、数据）

> 本 change 为纯文档整理（docs-only），在 `.openspec.yaml` 声明 `skip_specs: true`。

## Impact

- **文件**：`management/docs/`（新增 7 篇、删除被吸收的旧篇）、`docs/plans/`（清空）、`README.md`（重写）、`datasets/quadruped_action/README.md`（保留不动）
- **Web Wiki 页面**：management 路由递归扫描 `management/docs/`，文件增删自动反映到前端导航，无需改代码
- **不受影响**：所有代码、数据库、数据集、results 产物、`.claude/skills/`（agent 操作指南，与 wiki 分工见 design）、AGENTS.md（agent 专用，保留独立维护）
