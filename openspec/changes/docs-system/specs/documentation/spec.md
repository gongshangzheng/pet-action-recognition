## ADDED Requirements

### Requirement: 文档登记表为唯一权威

系统 SHALL 维护文档登记表（编号 / 标题 / slug / 职责边界 / 单篇 Change），作为文档体系所有「新增 / 废弃 / 职责归属」问题的唯一权威来源。

#### Scenario: 新增一篇 wiki

- **WHEN** 需要新增一篇 wiki 文档
- **THEN** 先在总 Change `docs-system` 登记编号与职责边界，再开单篇 Change `docs-<slug>`，design 审核通过后才动笔

#### Scenario: 内容归属有争议

- **WHEN** 一段内容不确定属于哪篇（如「模型内部设计」是否属于系统架构）
- **THEN** 按登记表的职责边界裁定：跨模型 → 6 号架构；单模型内部 → 8 号 Tokenizer

### Requirement: 章节列表对标题强调符号的处理

文档页右侧章节列表 SHALL 对 Heading 中的 Markdown 强调符号（`**`）做处理——丢弃或渲染为强调；MUST NOT 原样显示符号字符。

#### Scenario: 标题含加粗

- **WHEN** 某标题为 `### §4.2 视频编码器：**3D patchify**`
- **THEN** 章节列表显示「§4.2 视频编码器：3D patchify」（符号丢弃）或同等强调渲染，且不出现 `**` 字符

### Requirement: 演进记录存于元数据并按需展示

演进记录 SHALL NOT 作为正文章节；SHALL 支持在 YAML frontmatter（`changelog` 字段）以粗粒度（日期 + 一句话 + commit）写入；文档页头部 SHALL 提供按钮，点击后展示该文档的演进记录。

#### Scenario: 查看演进记录

- **WHEN** 读者打开带 `changelog` 的文档并点击头部的「演进记录」按钮
- **THEN** 展示演进记录列表；正文与右侧章节列表中均不出现演进记录章节

### Requirement: 结构级变更走单篇 Change 且 design 先行

结构级文档变更（章节增删 / 移动 / 重编号 / 内容定位变化）MUST 走单篇 OpenSpec Change，且 MUST 在 design.md 中写明目标结构（章节清单 / 每章职责 / 细章分解 / 读者动线）并经用户审核后方可动笔。内容级小修（错字 / 数字 / 单段论证 / 链接）直接修改，MUST 在 commit message 中说明。

#### Scenario: 重排章节

- **WHEN** 需要重排一篇文档的章节
- **THEN** 先在单篇 Change 的 design 写明新旧结构与重映射方案，审核通过后实施，并以「引用闭合核对（悬空 = 0）」作为完成标准
