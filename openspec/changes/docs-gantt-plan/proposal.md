# Proposal: docs-gantt-plan（《交付冲刺计划》单篇 Change）

## Why

11.13 硬件交付、11.18 内部封板、11.23 联合验收三节点已定，但排期原先散落在对话与 `milestones.md` 的粗略日期里：哪条线先做、哪项卡下游、卡住时降级到哪，没有一处写全。分散的后果已经出现过一次——把「端云协同支持」错记到算法线，实际是硬件组要提供给厂商的序列号与 SDK。

本 Change 建立 `management/docs/gantt-implementation-plan-202611.md` 作为**冲刺期排期的唯一入口**，并把它的登记补进文档体系。

## What Changes

- 登记新文档：编号 12，slug `gantt-implementation-plan-202611`，职责边界限定为「冲刺排期与分工」
- 确立该篇目标结构为唯一依据（见 design）：后续排期调整先改本 Change 的 design，再动正文
- 与 `milestones.md` 的关系写清：里程碑表管长期节点，本文管冲刺期逐日排布，两者日期必须一致，冲突以本文为准并回写里程碑表

## Capabilities

### documentation

- 冲刺排期的权威来源 SHALL 是本篇与 `openspec/registry.md` 的登记行，不得散落在对话或其他文档
- 排期变更 MUST 先改 design、再改正文、最后重渲染图，三者同步
- 图的源码（`.mmd`）、渲染结果（PNG/SVG）与正文 MUST 同一次提交入库

## Impact

- affected: `management/docs/gantt-implementation-plan-202611.md`、`management/docs/_assets/gantt-implementation-plan-202611/`、`openspec/registry.md`
- 归属：注册到文档登记表编号 12
- 关联：`management/milestones.md`（M3/M4 日期需与本文一致）
