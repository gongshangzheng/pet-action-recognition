# Tasks

## 1. 令牌与主题覆盖
- [x] 1.1 `styles/variables.scss`：`$text-secondary` → #4b5563，`$text-light` → #5f6672（与运行时令牌同源）
- [x] 1.2 `styles/index.scss`：`:root` 与 `[data-theme='dark']` 更新 `--color-text-secondary` / `--color-text-dim`
- [x] 1.3 `styles/index.scss`：补 `.visually-hidden`、`:focus-visible` 描边、`prefers-reduced-motion` 降级、文字选中色
- [x] 1.4 `App.vue`：`themeOverrides.common` 增加 `textColor3` / `placeholderColor`（明暗双档）

## 2. 页面结构
- [x] 2.1 `layouts/MainLayout.vue`：内容区改 `<main id="main">`、加跳转链接、按 `meta.ownHeading` 渲染隐藏 h1
- [x] 2.2 `layouts/MainLayout.vue`：顶栏窄屏适配（隐藏日期、面包屑截断、内边距）
- [x] 2.3 `router/index.js`：Doc/Report/Meeting 三条路由标 `meta.ownHeading`
- [x] 2.4 页内页面级 `h3`/`h4` 降为 `h2`（PaperList、EvalResults、TeamList、ModelManage、Home）

## 3. 键盘可达
- [x] 3.1 新增 `directives/clickable.js`，`main.js` 注册 `v-clickable`
- [x] 3.2 应用到 PaperList 卡片、DatasetBrowser 数据集卡与文件项、SpeedRun 视频卡、ProjectTaskNode 折叠箭头
- [x] 3.3 DocPage 侧栏 `<a>` 补 `href` + `@click.prevent`

## 4. 响应式
- [x] 4.1 Home / TaskBoard / TeamList / ModelManage / SpeedRun 的 `cols` 改断点写法
- [x] 4.2 验证 390 / 320 / 768 三档无横向溢出、无被裁切控件

## 5. 令牌化与对比度
- [x] 5.1 优先级标签：11px + 明暗双档色（TaskBoard、ProjectTaskNode）
- [x] 5.2 Home / TeamList / TaskBoard / MilestoneTimeline / SpeedRun / TrainRunDetail 硬编码色改 `var(--color-*)`
- [x] 5.3 Home 模块图标底色加深（白字达 3:1 以上）；SpeedRun 徽标底色加深
- [x] 5.4 `EvalOutputs` / `VideoModal` 的 `var(--color-text-dim, #9ca3af)` 兜底值同步

## 6. 细节
- [x] 6.1 TrainResults / SpeedRun 轮询随 `document.hidden` 暂停
- [x] 6.2 6 处 `<img>` 补 `alt`
- [x] 6.3 `size="tiny"` 刷新按钮高度 ≥24px
- [x] 6.4 `transition: all` 收敛为具体属性

## 7. 验证
- [x] 7.1 `npm run build` 通过
- [x] 7.2 detector 重扫 18 条路由 × 2 视口，对比修复前后计数
- [x] 7.3 自建脚本复测明暗两档对比度与 390/320 几何
- [x] 7.4 更新审计报告分数
