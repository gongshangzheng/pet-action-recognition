# Web 可访问性与响应式加固（审计后修复）

## Why

对 `web/` 全量路由做渲染态技术审计（detector + 计算色值/几何测量），得分 10/20（Acceptable）。实测问题集中在四类：

- 次要文字与占位符对比度不达 WCAG AA：`--color-text-dim` #9ca3af = 2.5:1（浅）/ #71717a = 3.4:1（深）；Naive 默认占位符 #c2c2c2 = 1.8:1，全站 127 处。
- 键盘不可达：`.paper-card` / `.ds-card` / `.browse-item` / `.video-card` / 文档侧栏链接均为 `div`/无 href 的 `a`，全库 0 处 `tabindex`/`role`。
- 手机端布局失效：`:cols="3"` 无断点，390px 下每列 87px；顶栏 `.header-right` 右边界 402px（视口 390），主题切换按钮被裁切。
- 主题漂移：14 个视图 100 处硬编码十六进制色，深色模式下沿用浅色值，同一批文字降到 3.1–3.7:1。

## What Changes

- 重建文字颜色阶梯：`--color-text-secondary` / `--color-text-dim` 明暗各取可达 AA 的值；Naive `themeOverrides.common` 补 `textColor3` / `placeholderColor`，修掉占位符与空态描述。
- 新增 `v-clickable` 指令（`role="button"` + `tabindex` + Enter/Space 触发 click），应用到 5 处可点卡片与文档侧栏链接。
- 页面结构：内容区改 `<main>`、加跳转链接、每页唯一 `h1`（视觉隐藏，来自 `route.meta.title`；Doc/Report/Meeting 已有可见 h1 的除外）；页内 `h3`/`h4` 当页面级标题时降为 `h2`。
- 响应式：5 处 `:cols="3"` 改 Naive 断点（`1 640:2 900:3` 一类），SpeedRun 断点顺序修正；顶栏窄屏隐藏日期、面包屑可截断、内边距收紧。
- 令牌化：Home / TaskBoard / TeamList / MilestoneTimeline / SpeedRun / TrainRunDetail / ProjectTaskNode 的硬编码色改 `var(--color-*)`；优先级标签改 11px + 明暗双档可达色；白字徽标底色加深。
- 细节：轮询随 `document.hidden` 暂停、6 处 `<img>` 补 alt、`size="tiny"` 刷新按钮提到 28px、`transition: all` 收敛到具体属性、补 `prefers-reduced-motion` 与 `:focus-visible`。

## Non-goals

- 不重做视觉方向、不动信息架构；不改后端与数据文件。
- 纸质模块（`PaperList` / `PaperDetail`）的 slate 调色板保持原样（属视觉方向，单独立项）。
- 不引入新依赖。

## Impact

- 影响代码：`web/src/styles/*`、`App.vue`、`layouts/MainLayout.vue`、`router/index.js`、`main.js`、新增 `directives/clickable.js`、7 个视图、2 个公共组件。
- 预期审计分从 10/20 提升到 16–18/20。
