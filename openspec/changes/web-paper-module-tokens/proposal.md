# 论文模块配色并入主题令牌

## Why

第一轮审计时 `papers.db` 为空，论文列表卡片没有渲染，所以没测到这一块。临时插入一条本地 demo 记录后实测（`tmp/audit/papers-contrast-before.json`），论文模块是**独立的 slate 调色板**（`#1e293b / #64748b / #94a3b8 / #f8fafc / #e2e8f0`），完全没有走 `--color-*` 令牌：

- 浅色下 6 处不达 AA：`.paper-title-en` 2.1:1、`.paper-date` 2.1:1、作者行 3.9:1、缩略图占位图标 2.3:1、来源标签 1.2:1。
- 深色下 11 处：`.stats-bar` 仍是 `#f8fafc` 白岛，`.stat-num` 变成 2.1:1；卡片仍是白底黑字，dark 模式形同失效。

## What Changes

- `PaperList.vue` / `PaperDetail.vue` 的 43 处硬编码色换成 `--color-*` 令牌（文本、卡片面、边框、悬停、阴影）。
- 语义修正：次要信息统一走 `--color-text-dim`，正文走 `--color-text-secondary`；来源标签走已有的 `--tag-medium-*`。
- 钉住态去掉 `border-left: 3px` 色条（超出 1px 的彩色左边框），只保留 `--color-primary-soft` 底色 + 📌 按钮标记。
- `.action-btn` 默认不透明度 0.25 → 0.45（可点性可见），悬停底色走 `--color-hover`。
- 外链按钮悬停改为 `--color-primary-soft` 底 + 主色边，不再用「主色实底 + 白字」（深色模式下强调色变亮，白字会失效）。

## Non-goals

- 不改论文模块的信息架构与交互。
- 不把 emoji 徽标（📝/✨/📌/⭐）换成图标系统——可读性不受影响，留作单独一项。

## Impact

- 代码：`web/src/views/papers/PaperList.vue`、`PaperDetail.vue`
- 预期：论文模块与全站主题一致，明暗两档对比度全部达标
