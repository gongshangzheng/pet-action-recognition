# Tasks: docs-gantt-plan

## 1. 建档与登记

- [x] 1.1 建立 `management/docs/gantt-implementation-plan-202611.md`（frontmatter `id: 12`）
- [x] 1.2 登记进 `openspec/registry.md` 编号 12，写明职责边界与单篇 Change 指向
- [x] 1.3 建立本 change（proposal / design / tasks）

## 2. 正文按 design 结构落盘

- [x] 2.1 一章「时间线」：11.13 硬件到手、11.18 内部封板、11.20 演练通过、11.23 联合验收
- [x] 2.2 二章「甘特图」：图片、图例、尺寸例外说明
- [x] 2.3 三章「三条并行线」：算法训练 / 硬件组 / 端云集成，表格含时间、工作、产出或依赖
- [x] 2.4 四章「检查节点」：时间、核验内容、不通过时的动作
- [x] 2.5 五章「与其他文档的关系」、六章「重新渲染」

## 3. 图与资产

- [x] 3.1 `.mmd` 源 + 渲染配置由 `report-figures` skill 统一，2 倍 PNG 与 SVG 同批产出
- [x] 3.2 资源放 `_assets/gantt-implementation-plan-202611/`，正文用 `/api/management/docs-assets/...` 绝对 URL
- [x] 3.3 甘特图关闭 `todayMarker`、`leftPadding` 留出泳道列，避免泳道名压任务条

## 4. 与其他文档对齐

- [x] 4.1 `milestones.md` 的 M3 / M4 日期改到与本文一致（M3 → 11-18 内部封板，M4 → 11-23 联合验收）
- [x] 4.2 `milestones.md` 风险表里「漏检率口径未定义 → 8 月内对齐」已过期，改为口径已定、未达标

## 5. 待用户确认后再做

- [ ] 5.1 本篇排期若再变，先改 design 再改正文，最后重渲染图
- [ ] 5.2 归档本 change（`openspec archive docs-gantt-plan`）
