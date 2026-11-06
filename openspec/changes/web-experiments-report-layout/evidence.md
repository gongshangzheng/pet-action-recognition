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
