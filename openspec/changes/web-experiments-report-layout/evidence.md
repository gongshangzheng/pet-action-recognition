# 证据

### 2026-11-07：版式改造首轮

- **1.1 决策**：章节导航放**右侧**，参考 `DocPage.vue`（侧栏 210px + 正文 + 右侧 TOC 180px，TOC 在 ≥1280px 显示）。用户指示“参考文档页”，据此落定。
- **1.2 基线证据**：
  - `ExperimentsPage.vue` 改造前为两张堆叠 `n-card`，列表与三个 `n-select` 混在 `n-card` 的 `header` 中。
  - 正文宽度限制：`.detail-article { max-width: 76ch }`（改造前第 403 行）。
  - `DocPage.vue`：`.doc-page` flex 纵向，≥1024px 转横向；`.doc-sidebar` 210px（<1024px 隐藏，另用 `.doc-mobile-select` 顶部下拉）；`.doc-toc` 180px（≥1280px）；`.doc-content` 为卡片容器。
- **改造内容**：页面结构改为 `doc-page` 三栏（侧栏 = 筛选 + 报告列表，正文 = 报告，右侧 = 章节目录）；去掉 `n-card` 包裹与 `n-card-header`；报告标题改为页面唯一 `h1`；正文段落限宽 78ch，表格/代码/图占满正文区，表格容器独立横向滚动；<1024px 侧栏隐藏、改用顶部下拉选报告，<1280px 隐藏目录。
- **构建**：`npx vite build` 通过（仅有既存的大 chunk 警告）。
- **静态检查**：`impeccable detect --json` 对改动文件返回空（无机械检出项）。
- **未完成**：浏览器视觉核对（1440 / 1024 / 768 三档）。本机没有 Chrome/Chromium 可做无头截图，需由用户在已打开的前端页面确认；确认前 3.1–3.4 保持未勾选。

### 2026-11-07：验收状态（视觉核对受阻）

- **3.2 交互核对（代码层）**：筛选由 `filteredReports` 计算属性驱动；选中状态由 `route.query.topic/slug` 决定并同步；`isActive`/`detailHref` 未改动；列表未引入轮询，`keep-alive` 行为不受影响。
- **3.3 构建与静态检查**：`npx vite build` 通过（仅既存大 chunk 警告）；`impeccable detect --json` 对该文件返回空。
- **3.1 三档视觉核对：无法在本机完成**。环境只有 Safari：`osascript` 打开页面成功，但 `screencapture` 报 `could not create image from rect`（终端未获屏幕录制权限）；本机也没有 Chrome/Chromium/Playwright 浏览器可做无头截图。安装无头浏览器属新的执行动作，需另行批准。
- **3.4 用户审阅**：保持未勾选，等用户在三档宽度下确认；未确认前不改动其它页面。
