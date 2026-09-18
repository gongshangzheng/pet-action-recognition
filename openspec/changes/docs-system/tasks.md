# Tasks: docs-system

## 1. 体系治理

- [x] 1.1 文档登记表落库（本 design）
- [x] 1.2 职责边界裁定：跨模型 → 6 号；单模型内部 → 8 号（2026-09-17 三节迁移）
- [x] 1.3 流程写入 documentation skill §0
- [ ] 1.4 各篇补齐单篇 Change（按需，结构级变更时开）

## 2. 引用健康

- [x] 2.1 架构文档引用闭合核对（悬空 = 0，2026-09-17）
- [ ] 2.2 其余篇目引用闭合核对（逐篇，结构级变更时顺带）

## 3. 文档系统功能（前端 / 渲染层）

- [ ] 3.1 TOC 强调符号处理：章节列表丢弃（或渲染）标题中的 `**`，不显示符号字符（`extractToc`）
- [ ] 3.2 **sidecar json 约定**：字段 schema（changelog / progress / appendix / related）+ 后端 `get_doc_detail` 读取同名 `<slug>.json` 一并返回
- [ ] 3.3 **渲染**：DocPage 顶部按钮（演进记录 / 进度，弹层）+ 底部独立块（相关文档 / 附录）；架构文档（6 号）元数据迁入 sidecar（配合 `docs-architecture` v7 实施）
