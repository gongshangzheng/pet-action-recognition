# Tasks: doc-page-collapsible-panels

## 1. 状态与持久化

- [x] 1.1 在 `DocPage.vue` 增加 `sidebarCollapsed` / `tocCollapsed` 两个 ref，初始值从 localStorage（`doc-page.sidebar-collapsed` / `doc-page.toc-collapsed`）读取，读写用 try/catch 包裹
- [x] 1.2 增加切换函数 `toggleSidebar()` / `toggleToc()`，切换时同步写回 localStorage

## 2. 模板改造

- [x] 2.1 左栏：标题行 `文档` 旁加收起按钮（chevron-left 图标，title="收起"），点击置 `sidebarCollapsed = true`
- [x] 2.2 左栏收起态：`v-else` 渲染 28px 贴边窄带，内含展开按钮（chevron-right，title="展开文档列表"）
- [x] 2.3 右栏：`目录` 标题行旁加收起按钮（chevron-right），收起后渲染 28px 贴边窄带 + 展开按钮（chevron-left）；窄带沿用 `v-if="tocItems.length"` 条件
- [x] 2.4 引入 `@vicons/ionicons5` 的 chevron 图标与 `n-icon` 组件

## 3. 样式

- [x] 3.1 `.doc-sidebar.collapsed` / `.doc-toc.collapsed`：宽度 28px，隐藏原内容容器，窄带 sticky 于顶部
- [x] 3.2 左栏窄带仅在 ≥1024px 显示，右栏窄带仅在 ≥1280px 显示（沿用现有断点媒体查询）
- [x] 3.3 按钮样式：透明背景、hover 高亮，与 Projects.vue 的 `.progress-toggle` 风格一致

## 4. 验证

- [x] 4.1 手动验证：收起左栏 → 正文占满左侧、左缘留把手；点把手恢复；右栏同理；两栏同时收起正常
- [x] 4.2 刷新页面后收起状态保持
- [x] 4.3 视口缩到 <1024px：左栏与左把手消失，移动端下拉选择器可用；<1280px：右栏与右把手消失
- [x] 4.4 无 TOC 的文档：右栏与右把手均不出现
- [x] 4.5 `npm run check` / 构建通过（项目无 check 脚本，用 `npx vite build` 验证通过）
