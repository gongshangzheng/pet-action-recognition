# Tasks: docs-system

## 1. 体系治理

- [x] 1.1 文档登记表落库（本 design）
- [x] 1.2 职责边界裁定：跨模型 → 《系统架构》；单模型内部 → 《动作识别模型设计》（2026-09-17 三节迁移）
- [x] 1.3 流程写入 documentation skill §0
- [x] 1.4 各篇补齐单篇 Change（按需，结构级变更时开）— 机制已建立并被执行：《系统架构》→ `docs-architecture`、《动作识别模型设计》→ `docs-action-model-design`，均已归档；其余篇目未发生结构级变更，本项不产生新的单篇 Change

## 2. 引用健康

- [x] 2.1 架构文档引用闭合核对（悬空 = 0，2026-09-17）
- [x] 2.2 其余篇目引用闭合核对（逐篇，结构级变更时顺带）— 已全量核对：`python3 scripts/checks/check_doc_refs.py` 覆盖 `management/docs/`、`papers/docs/` 与未归档 change 的 proposal/design/tasks 解析成功 46 条、**悬空 0**（本次共修复 22 条历史悬空引用；来源文件数随未归档 change 增减）

## 3. 文档系统功能（前端 / 渲染层）

- [x] 3.1 TOC 强调符号处理：章节列表丢弃（或渲染）标题中的 `**`，不显示符号字符（`extractToc`）
- [x] 3.2 **sidecar json 约定**：字段 schema（changelog / progress / appendix / related）+ 后端 `get_doc_detail` 读取同名 `<slug>.json` 一并返回
- [x] 3.3 **渲染**：DocPage 顶部按钮（演进记录 / 进度，弹层）+ 底部独立块（相关文档 / 附录）；架构文档（《系统架构》）元数据迁入 sidecar（`architecture.json` 已建，尾章已迁出）

## 渲染层修复

- [x] Mermaid 文本截断：`htmlLabels: false` + fontFamily 取页面计算字体（中文/符号标签不再被裁）
