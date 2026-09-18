# Proposal: docs-architecture（6 号《系统架构》单篇 Change）

## Why

6 号《系统架构》（`management/docs/architecture.md`）是所有「结构 / 设计」问题的唯一入口。2026-09-17 经多轮局部盲改后严重混乱（内容错位 / 编号错乱 / 引用悬空），已做一次全文通读后的重组；本 Change 此后作为该篇的唯一管理入口，保证后续变更不再失序。

## What Changes

- 记录 2026-09-17 已实施的**章节重组**（结构见 design，含总图前置、流程独立成章、模型内设计移交 8 号、推理形态（原C18，已裁定） 落盘）
- 确立该篇的**目标结构为唯一依据**：后续一切结构变更先改本 Change 的 design、经审核再动笔

## Capabilities

### documentation
- 章节结构与职责 SHALL 以本 Change design 为唯一依据
- 结构级变更 MUST 先修订 design 并经审核

## Impact

- affected: `management/docs/architecture.md`
- 归属：总 Change `docs-system` 登记表第 6 号
