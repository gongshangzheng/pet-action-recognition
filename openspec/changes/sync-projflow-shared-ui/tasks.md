## 1. 主题色与图标配置

- [x] 1.1 新增 `web/src/config/theme.js`（取上游：`ACCENTS` 9 色 / `DEFAULT_ACCENT='gray'` / `mix` / `toRgba` / `accentFor` / `accentThemeOverrides` / `readableOn`）
- [x] 1.2 新增 `web/src/config/favicon.js`（取上游：6 形状 / `faviconSvg` / `faviconDataUrl` / `isFaviconKey`）
- [x] 1.3 新增 `web/src/config/layout.js`（取上游：`SIDEBAR_DEFAULT_COLLAPSED = true`）

## 2. 状态与注入

- [x] 2.1 重写 `web/src/stores/theme.js`：保留 `detectInitial()` 与本仓库键前缀，新增 `accent` / `favicon` 状态与 `setAccent()` / `setFavicon()`、`applyAccent()`、`applyFavicon()`
- [x] 2.2 `web/src/App.vue`：`themeOverrides` → `computed` + `accentThemeOverrides`（保留 `naiveTheme` 与 `watch` 兜底）
- [x] 2.3 `web/src/styles/variables.scss`：`$primary-color/-light/-dark` → `#4a4f57 / #60646b / #41464d`
- [x] 2.4 `web/src/styles/index.scss`：`:root` 与 dark 的 `--color-primary` / `-soft` / `--color-selected` 同步，并新增 `--color-primary-border`

## 3. MainLayout 合入

- [x] 3.1 侧边栏 props：`n-layout-sider` / `n-menu` 折叠宽 `64 → 56`，折叠图标 `22 → 18`；`.logo-icon` 字号适配
- [x] 3.2 折叠持久化：键 `pet-action-recognition-sidebar-collapsed`，`readCollapsed()` / `watch` 写回（不设 immediate），初值走 `SIDEBAR_DEFAULT_COLLAPSED`
- [x] 3.3 顶栏弹层：调色盘按钮 + `n-popover`「主题色」色块网格 +「图标」6 个预览（`v-html="faviconSvg(f.key, themeStore.accentPrimary)"`）
- [x] 3.4 弹层样式（`.theme-panel` / `.accent-grid` / `.accent-swatch` / `.favicon-grid` / `.favicon-option`）

## 4. 文档页与清理

- [x] 4.1 `DocPage.vue`：`.doc-sidebar.collapsed` / `.doc-toc.collapsed` `28px → 20px`；`.panel-strip-label` `10px / 字距 1px`
- [x] 4.2 `web/public/favicon.svg`：替换为「枪灰底 + 白色闪电」静态兜底
- [x] 4.3 删除 `web/public/icons.svg`（已确认无引用）

## 5. 验证

- [x] 5.1 dev 下切换强调色（枪灰/青色/玫红）：主色元素与 Naive 组件同步（`--color-primary` 与 `--n-item-text-color-active` 同值）
- [x] 5.2 弹层「图标」6 个预览可切换，标签页图标随之变化并持久化；未知 key 回落闪电
- [x] 5.3 折叠侧边栏后刷新保持折叠；展开后刷新保持展开；删除该 key 后回到默认折叠
- [x] 5.4 折叠态实测：侧边栏 ≈56px、图标 18px；文档页折叠条 20px、竖排标签未裁切
- [x] 5.5 明暗切换后强调色取对应模式色值；`pet-action-recognition-theme` 未被覆盖
- [x] 5.6 `npm run build` 通过；Pages 产物仍含 `docs-data.json` 与 `404.html`
- [x] 5.7 `openspec validate sync-projflow-shared-ui` 通过

## 6. 收尾

- [x] 6.1 提交（`[shared]` 前缀）
