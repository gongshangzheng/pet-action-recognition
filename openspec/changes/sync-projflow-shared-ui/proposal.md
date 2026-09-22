# Proposal: sync-projflow-shared-ui（同步上游主题色 / favicon / 折叠改进）

## Why

上游 ProjFlow 在 `web/` 共享脚手架层落了一批 UI 改进，本仓库尚未同步，导致两个仓库体验不一致、且上游后续改动会持续分叉：

| 上游 commit | 内容 | 本仓库现状 |
|-------------|------|-----------|
| `0799f7e` | 强调色（主题色）可切换 + 调色盘 + 折叠态尺寸收缩 | 无 |
| `2fbb3a6` / `888ef3f` | 枪灰预设 + 默认强调色改为枪灰、同步兜底色值 | 无 |
| `1341f31` | favicon 跟随主题 + 6 种图标形状可切换 | 无（图标是脚手架的紫色死文件） |
| `8b54bab` | 侧边栏折叠状态持久化 + 首次默认折叠 | 无（刷新回弹） |
| `50b7a5b` | 清理残留硬编码主色 + 删除死资源 `icons.svg` | 无 |

`web/` 与共享 skill 属上游所有（见 `upstream-sync` 铁律），因此应取上游实现而不是本地另写。

## What Changes

**主题色**

- 新增 `web/src/config/theme.js`（强调色唯一数据源：9 色预设 + `mix`/`toRgba`/`accentFor`/`accentThemeOverrides`/`readableOn`）。
- 重写 `web/src/stores/theme.js`：新增 `accent` / `favicon` 状态与 `setAccent()` / `setFavicon()`；`applyAccent()` 写 `<html>` 的 `--color-primary` / `-soft` / `-selected` / `-border`。**存储键沿用本仓库前缀**（`pet-action-recognition-theme` / `-accent` / `-favicon`）。
- `web/src/App.vue`：`themeOverrides` 由静态常量改为 `computed`，与 CSS 变量同源。
- `web/src/styles/variables.scss`：`$primary-*` 改为枪灰族。
- `web/src/styles/index.scss`：`:root` 与 dark 的兜底令牌同步，新增 `--color-primary-border`。

**favicon**

- 新增 `web/src/config/favicon.js`（6 个自绘形状；`faviconSvg` 用「强调色圆角块 + 自动对比色前景」）。
- `web/src/layouts/MainLayout.vue`：顶栏调色盘按钮的弹层扩展为「主题色 + 图标」两节。
- `web/public/favicon.svg`：替换为「枪灰底 + 白色闪电」的静态兜底（原文件是从脚手架带进来的紫色生成器产物，与本仓库主题无关）。

**折叠**

- 新增 `web/src/config/layout.js`（`SIDEBAR_DEFAULT_COLLAPSED`）。
- `MainLayout.vue`：折叠状态持久化 + 首次默认折叠；`n-layout-sider` / `n-menu` 折叠宽 `64 → 56`、折叠图标 `22 → 18`。
- `DocPage.vue`：左右折叠条 `28px → 20px`，竖排标签 `11px/字距2 → 10px/字距1`。

**清理**

- 删除 `web/public/icons.svg`（未被引用的死文件）。

> 上游 `4a3b964`（「根目录不设 `docs/`」+ `AGENTS.md` 删条目）**不适用于本仓库**：本仓库有意保留根目录
> `docs/` 存放原始设计文档（如 `宠物动作识别研究计划.docx`），wiki 文档另在 `management/docs/`。

## Capabilities

### New Capabilities

- `theme-accent`: 强调色预设、切换入口、持久化与明暗适配；主色不得硬编码。
- `theme-favicon`: 站点图标跟随强调色/明暗、多形状可选与持久化、无 JS 兜底。
- `sidebar-collapse`: 主侧边栏折叠状态持久化、首次默认值与折叠态尺寸。

### Modified Capabilities

（无）

## Impact

- 前端：新增 `web/src/config/{theme,favicon,layout}.js`；修改 `web/src/stores/theme.js`、`web/src/App.vue`、`web/src/layouts/MainLayout.vue`、`web/src/views/management/DocPage.vue`、`web/src/styles/{index,variables}.scss`、`web/public/favicon.svg`；删除 `web/public/icons.svg`。
- 后端：**不动**（上游 `644fed0` 的排序链与 `DOCS_FOLDER_ORDER` 属另一批，见 Non-Goals）。
- 行为变化：主色可切换并持久化；标签页图标随主题变化且形状可选；侧边栏折叠偏好跨刷新保留、首次默认折叠、折叠态更窄。
- 归属：共享脚手架层 → 提交加 `[shared]` 前缀。
