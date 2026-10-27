# documentation Specification

## Purpose
TBD - created by archiving change docs-architecture. Update Purpose after archive.
## Requirements
### Requirement: 章节结构以本 Change design 为唯一依据

每篇结构级文档（《系统架构》《动作识别模型设计》等）的章节清单、每章职责与细章分解 SHALL 以该篇单篇 Change design 的「章节清单」为唯一依据；结构级变更 MUST 先修订 design 并经用户审核，之后才能改正文。

#### Scenario: 请求把模型内部设计写回架构文档

- **WHEN** 有人想把聚合粒度 / 离散化 / 对称架构等单模型内容写回架构文档
- **THEN** 按 design 的边界裁定移交给 《动作识别模型设计》，架构文档只保留跨模型视角

#### Scenario: 请求把跨模型内容写进 《动作识别模型设计》

- **WHEN** 有人想把实时性 / 流式、门控、跨模型协作等跨环节内容写进 《动作识别模型设计》
- **THEN** 按 `docs-system` 的职责裁定移交 《系统架构》，《动作识别模型设计》只保留单模型内部设计

#### Scenario: 请求改 《动作识别模型设计》章节结构

- **WHEN** 有人要求调整 《动作识别模型设计》的章节顺序或拆分方式
- **THEN** 先修订本 Change design 的目标结构与读者动线，经用户审核后再动正文

### Requirement: 引用闭合

结构级文档内与指向结构级文档的节引用 SHALL 全部可解析（引用 → 标题闭合，悬空 = 0）；章节编号重排 MUST 级联全仓引用（《系统架构》/《动作识别模型设计》/ papers 笔记 / 各 change design）并核对。

#### Scenario: 章节重编号后

- **WHEN** 章节编号发生变化
- **THEN** 全仓跨文档引用级联重映射，并以「引用 → 标题闭合核对（悬空 = 0）」作为任务完成标准

#### Scenario: 闭合核验可重复执行

- **WHEN** 需要确认引用是否闭合
- **THEN** 运行 `python3 scripts/checks/check_doc_refs.py`，悬空数为 0 且非零退出码不再出现

### Requirement: 文档登记表为唯一权威

系统 SHALL 维护文档登记表（编号 / 标题 / slug / 职责边界 / 单篇 Change），作为文档体系所有「新增 / 废弃 / 职责归属」问题的唯一权威来源。

#### Scenario: 新增一篇 wiki

- **WHEN** 需要新增一篇 wiki 文档
- **THEN** 先在总 Change `docs-system` 登记编号与职责边界，再开单篇 Change `docs-<slug>`，design 审核通过后才动笔

#### Scenario: 内容归属有争议

- **WHEN** 一段内容不确定属于哪篇（如「模型内部设计」是否属于系统架构）
- **THEN** 按登记表的职责边界裁定：跨模型 → 《系统架构》架构；单模型内部 → 《动作识别模型设计》 Tokenizer

### Requirement: 章节列表对标题强调符号的处理

文档页右侧章节列表 SHALL 对 Heading 中的 Markdown 强调符号（`**`）做处理——丢弃或渲染为强调；MUST NOT 原样显示符号字符。

#### Scenario: 标题含加粗

- **WHEN** 某标题为 `### §4.2 视频编码器：**3D patchify**`
- **THEN** 章节列表显示「§4.2 视频编码器：3D patchify」（符号丢弃）或同等强调渲染，且不出现 `**` 字符

### Requirement: 文档元数据存于同名 sidecar json

每篇文档（`<slug>.md`）SHALL 支持同名 sidecar json（`<slug>.json`）承载元数据：`changelog`（演进：日期 + 一句话 + commit）、`progress`（进度）、`appendix`（附录设计说明）、`related`（相关文档）。这些元数据 SHALL NOT 出现在正文章节与章节列表中。

#### Scenario: 更新演进记录

- **WHEN** 某文档发生一次值得记录的演进
- **THEN** 只更新 `<slug>.json` 的 `changelog`（追加：日期 + 一句话 + commit），正文不变、不触发章节重排

### Requirement: 元数据的渲染布局

文档页 SHALL 在**文章顶部**提供按钮展示演进记录与进度（点击弹层）；SHALL 在**文章底部**以独立块渲染相关文档与附录；无对应字段的文档 MUST NOT 渲染空块。

#### Scenario: 打开带完整 sidecar 的文档

- **WHEN** 读者打开 `architecture.md`（其 `architecture.json` 含全部四字段）
- **THEN** 顶部可见「演进记录」「进度」按钮，点击弹层展示；页面底部出现「相关文档」与「附录」独立块；正文与章节列表不含这些内容

#### Scenario: 无 sidecar 的文档

- **WHEN** 某文档没有同名 json 或 json 为空
- **THEN** 不渲染顶部按钮与底部块，页面正常

### Requirement: 结构级变更走单篇 Change 且 design 先行

结构级文档变更（章节增删 / 移动 / 重编号 / 内容定位变化）MUST 走单篇 OpenSpec Change，且 MUST 在 design.md 中写明目标结构（章节清单 / 每章职责 / 细章分解 / 读者动线）并经用户审核后方可动笔。内容级小修（错字 / 数字 / 单段论证 / 链接）直接修改，MUST 在 commit message 中说明。

#### Scenario: 重排章节

- **WHEN** 需要重排一篇文档的章节
- **THEN** 先在单篇 Change 的 design 写明新旧结构与重映射方案，审核通过后实施，并以「引用闭合核对（悬空 = 0）」作为完成标准

