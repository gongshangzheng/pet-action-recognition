## Purpose

定义论文库的收录来源、入库与去重规则，以及核心论文（starred/pinned）标记标准与清单产出，使论文模块从空库状态变为可用、可检索、重点突出的文献库。

## ADDED Requirements

### Requirement: 存量博客论文入库

系统 SHALL 将 `data/extracted_papers.json` 中的论文条目导入 `data/papers.db` 的 `papers` 表，并尽力通过 arXiv API 补全元数据（abstract、authors、published_at、arxiv_categories 等）。

#### Scenario: 首次导入存量论文

- **WHEN** 在空库状态下执行导入流程
- **THEN** `papers` 表中包含 extracted_papers.json 中全部可解析条目，且每条具有 id、title、url、source 字段

#### Scenario: arXiv 元数据补全

- **WHEN** 条目带有可用 arXiv ID
- **THEN** 该条目的 abstract、authors（JSON 数组字符串）、published_at、arxiv_categories 被从 arXiv API 补全；补全失败时条目仍入库且相关字段为 NULL 而非空字符串

### Requirement: 新论文调研收录

系统 SHALL 支持将动作识别与动物动作/行为特征方向新调研的论文收录进论文库，来源标记为 `arxiv` 或 `manual`。

#### Scenario: 收录新调研论文

- **WHEN** 调研产出一批候选论文（含 arXiv ID 或标题/链接）
- **THEN** 候选论文经过去重后被写入 `papers` 表，source 字段正确标记来源

#### Scenario: 新论文覆盖方向

- **WHEN** 收录完成
- **THEN** 论文库同时覆盖「视频动作识别方法/数据集」与「动物姿态估计/动物行为识别/动物动作数据集」两个方向的文献

### Requirement: 去重与幂等

系统 SHALL 保证导入流程可重复执行：同一篇论文（按 arXiv ID 优先、标题归一化次之判定）在库中最多存在一条记录。

#### Scenario: 重复执行导入

- **WHEN** 对已导入过的数据再次执行导入流程
- **THEN** 数据库中不出现重复记录，已有记录的 starred/pinned/note 等用户数据不被覆盖

#### Scenario: 新旧来源去重

- **WHEN** 新调研论文与存量博客论文存在重叠
- **THEN** 仅保留一条记录，且保留已有记录的用户标记与笔记

### Requirement: 核心论文标记

系统 SHALL 依据明确标准（奠基性/高影响力、与宠物动作识别项目的训练或评测直接相关、动物动作方向代表性工作）筛选核心论文，并在数据库中以 `pinned`（最重要，置顶展示）与 `starred`（核心收藏）标记。

#### Scenario: 标记核心论文

- **WHEN** 核心论文筛选完成
- **THEN** 入选论文的 starred=1，其中最重要的一批 pinned=1，且标记可通过 `/api/papers?starred=true`、`/api/papers?pinned=true` 查询到

#### Scenario: 标记可复核

- **WHEN** 查看核心论文标记结果
- **THEN** 每篇核心论文的入选理由可追溯（在清单文档或论文笔记中有记录）

### Requirement: 核心论文清单产出

系统 SHALL 产出一份中文核心论文清单文档，按主题分组，每篇包含标题、年份/出处、一句话价值说明与链接。

#### Scenario: 生成清单文档

- **WHEN** 核心论文标记完成
- **THEN** 仓库内存在核心论文清单文档，且清单内容与数据库中 starred/pinned 标记一致
