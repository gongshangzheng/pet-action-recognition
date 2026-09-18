## ADDED Requirements

### Requirement: 章节结构以本 Change design 为唯一依据

架构文档的章节清单、每章职责与细章分解 SHALL 以本 Change design 的「章节清单」为唯一依据；结构级变更 MUST 先修订 design 并经用户审核。

#### Scenario: 请求把模型内部设计写回架构文档

- **WHEN** 有人想把聚合粒度 / 离散化 / 对称架构等单模型内容写回架构文档
- **THEN** 按 design 的边界裁定移交给 8 号《身份-动作 Tokenizer》，架构文档只保留跨模型视角

### Requirement: 引用闭合

架构文档内与指向架构文档的节引用 SHALL 全部可解析（引用 → 标题闭合，悬空 = 0）；编号重映射 MUST 级联全仓引用并核对。

#### Scenario: 章节重编号后

- **WHEN** 章节编号发生变化
- **THEN** 全仓跨文档引用级联重映射，并以「引用 → 标题闭合核对（悬空 = 0）」作为任务完成标准
