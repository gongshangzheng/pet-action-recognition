# Proposal: seed-papers-library

## Why

论文库当前是空的（`data/papers.db` 0 篇）——从博客提取的 140 篇论文只躺在 `data/extracted_papers.json` 里，从未入库；同时平台聚焦「宠物动作识别」，但论文库缺少动物动作识别/动物姿态与行为特征方向的文献覆盖。这导致论文列表页无数据可用，团队也没有一份可查阅的核心论文清单。

## What Changes

- **导入存量论文**：运行导入流程，把 `data/extracted_papers.json` 中 140 篇博客提取论文写入 `data/papers.db`（含 arXiv 元数据补全）
- **补充调研新论文**：围绕以下方向检索并入库新论文（调研已完成，77 条候选，去重后入库）：
  - 动作识别前沿（2022–2025，比 VideoMAE 更新/更好的模型）
  - 动物姿态估计与动物行为/动作识别
  - 核心问题一：动物动作数据稀缺（few-shot、自监督预训练、合成数据）
  - 核心问题二：人类动作识别能力迁移到动物（跨域/跨物种迁移）
- **核心论文标记**：按既定标准（奠基性、被引影响力、与本项目训练/评测直接相关性）筛选核心论文，在数据库中标记 `starred`（核心）与 `pinned`（最重要、置顶展示）
- **核心论文清单**：产出一份核心论文清单文档（中文，含每篇一句话价值说明），供团队查阅
- **去重与幂等**：新收录论文与存量 140 篇按 arXiv ID / 标题去重；导入流程可重复执行不产生重复记录

## Capabilities

### New Capabilities

- `papers-library`: 论文库的收录来源、入库规则、去重与幂等约束、核心论文（starred/pinned）标记标准与清单产出

### Modified Capabilities

（无）

## Impact

- **数据**：`data/papers.db`（gitignored，运行时数据）、`data/extracted_papers.json`（可能补充新提取条目）
- **脚本**：`scripts/import_papers.py`（如需修复/扩展以支持幂等导入与新来源）；可能新增 `scripts/curate_core_papers.py`（核心标记）与补充调研脚本
- **文档**：新增核心论文清单文档（`papers/docs/` 或 `management/docs/`）
- **前端**：无代码改动；论文列表页将有数据可看，置顶论文优先展示
- **外部依赖**：arXiv API（元数据获取）；不涉数据库迁移、不涉远程服务器

## 假设记录

- 「核心论文提出来给我」= 数据库内 starred/pinned 标记 + 一份中文清单文档 + 会话内汇报摘要
- 新调研论文来源以 arXiv 为主；无法获取 arXiv 元数据的条目以 `manual` 来源入库
- 核心论文规模预期 10–20 篇 pinned/starred；用户点名锚点：Two-Stream、I3D、SlowFast、VideoMAE、DeepLabCut、Animal Kingdom
- 调研 agent 环境无 web_search，所有 arXiv ID 凭训练知识给出，入库前必须经 arXiv API 核验（设计 D4 的降级机制兜底）
