# Proposal: docs-system（文档体系总 Change）

## Why

wiki 已有 11 篇（management/docs/）+ papers/docs 研究笔记若干。经多轮迭代出现：职责边界漂移、同一主题两篇文档重复、编号引用失真、无单一登记处。架构文档 2026-09-17 的混乱重组直接暴露了这一点——文档体系需要唯一管理入口。

## What Changes

- 建立**文档登记表**（本 Change design 内，唯一权威）：每篇文档的编号 / 标题 / slug / 职责边界 / 相互关系 / 对应单篇 Change
- 确立**双层流程**：总 Change（本 Change）管体系；单篇 Change（`docs-<slug>`）管一篇——规则详见 `.claude/skills/documentation/SKILL.md` §0
- 跨文档引用规范：`[N 号《标题》](./<slug>.md)`；引用必须指向真实存在的标题锚
- **文档系统功能（前端 / 渲染层）**：
  - **TOC 强调符号处理**：文档页右侧章节列表不渲染 Markdown 加粗符号，但 Heading 中常含 `**` → 展示时须**丢弃或渲染**，不得原样显示符号
  - **演进记录元数据化**：演进记录不再作为正文章节；支持在 frontmatter（`changelog` 字段）写入，文档页头部提供**按钮**按需展示

## Capabilities

### documentation
- 文档登记表 SHALL 为文档体系的唯一权威
- 新增 / 废弃一篇文档 MUST 在本 Change 登记（或开新的体系级 Change）
- 结构级文档变更 MUST 走单篇 Change，且 design 先行

## Impact

- affected: `management/docs/**`、`.claude/skills/documentation/SKILL.md`、`openspec/changes/docs-*`
- 不影响：`server/`、`web/` 代码
