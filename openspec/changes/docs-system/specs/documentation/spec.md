## ADDED Requirements

### Requirement: 文档登记表为唯一权威

系统 SHALL 维护文档登记表（编号 / 标题 / slug / 职责边界 / 单篇 Change），作为文档体系所有「新增 / 废弃 / 职责归属」问题的唯一权威来源。

#### Scenario: 新增一篇 wiki

- **WHEN** 需要新增一篇 wiki 文档
- **THEN** 先在总 Change `docs-system` 登记编号与职责边界，再开单篇 Change `docs-<slug>`，design 审核通过后才动笔

#### Scenario: 内容归属有争议

- **WHEN** 一段内容不确定属于哪篇（如「模型内部设计」是否属于系统架构）
- **THEN** 按登记表的职责边界裁定：跨模型 → 6 号架构；单模型内部 → 8 号 Tokenizer

### Requirement: 结构级变更走单篇 Change 且 design 先行

结构级文档变更（章节增删 / 移动 / 重编号 / 内容定位变化）MUST 走单篇 OpenSpec Change，且 MUST 在 design.md 中写明目标结构（章节清单 / 每章职责 / 细章分解 / 读者动线）并经用户审核后方可动笔。内容级小修（错字 / 数字 / 单段论证 / 链接）直接修改，MUST 在 commit message 中说明。

#### Scenario: 重排章节

- **WHEN** 需要重排一篇文档的章节
- **THEN** 先在单篇 Change 的 design 写明新旧结构与重映射方案，审核通过后实施，并以「引用闭合核对（悬空 = 0）」作为完成标准
