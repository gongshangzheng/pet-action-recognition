# Design: doc-page-collapsible-panels

## 背景

`web/src/views/management/DocPage.vue` 是三栏 flex 布局：

```
.doc-page (flex, gap 24px)
├── .doc-sidebar   210px，≥1024px 显示（display:none/block 切换）
├── .doc-article   flex:1
└── .doc-toc       180px，≥1280px 显示（display:none/block 切换，且 v-if="tocItems.length"）
```

仓库内已有同类交互先例：`Projects.vue` 的进展记录侧栏（`collapsed` class + 窄条上的展开按钮），本设计沿用该模式。

## 方案

### 状态

```js
const sidebarCollapsed = ref(false)  // 左栏
const tocCollapsed = ref(false)      // 右栏
```

初始值从 localStorage 读取（key：`doc-page.sidebar-collapsed` / `doc-page.toc-collapsed`），切换时写回。读写用 try/catch 包裹（隐私模式/禁用 localStorage 时不抛错，回退默认展开）。

### 模板与交互

- 每个侧栏头部（`文档` / `目录` 标题行）加一个收起按钮（`‹` / `›` 图标，hover 提示"收起"）
- 收起时 `<aside>` 渲染为一条贴边窄带（宽 28px，flex-shrink:0），带竖排或居中的展开按钮（`›` / `‹`），点击恢复
- 窄带位置对齐 flex 布局：左栏窄带在最左，右栏窄带在最右，中间正文自动占满剩余空间——无需手动计算宽度

### 样式实现要点

- `collapsed` 状态用 `:class` 绑定到 aside 上
- 收起态：`width: 28px`，内部 `.doc-sidebar-inner` / `.doc-toc-inner` 隐藏，只渲染窄带内容（用 `v-if`/`v-else` 分支，避免 sticky 容器干扰）
- 保持 `position: sticky; top: 16px` 的窄带把手在视口内
- 图标用 chevron（与 Projects.vue 一致，`chevron-back-outline` / `chevron-forward-outline`）

### 响应式配合

- 左栏窄带把手仅在 `@media (min-width: 1024px)` 下显示，右栏窄带仅在 `@media (min-width: 1280px)` 下显示——与现有断点一致，窄屏自动隐藏
- 右栏本身有 `v-if="tocItems.length"`，收起窄带沿用同一条件

### 不做的事

- 不加拖拽调宽（用户没要求，保持简单）
- 不改 `MainLayout.vue`、不改路由、不动后端

## 备选方案

- **方案 B：收起后把手浮在正文边缘（absolute 定位半透明按钮）**——视觉更"隐形"，但遮挡正文内容，且需处理滚动/层级；不如窄带直观，放弃
- **方案 C：浮层式侧栏（收起后 hover 边缘滑出）**——交互复杂度高，与现有 Projects.vue 模式不一致，放弃
