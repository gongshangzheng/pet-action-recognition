## Why

实验报告页与项目既有的文档页差得很远：报告列表和筛选器塞在一张 `n-card` 的 header 里，正文又被 `.detail-article { max-width: 76ch }` 压窄，指标表格和案例图因此挤在一条窄栏中；页面没有章节导航，长报告只能靠滚动寻找「结果与分析」。同一产品里两种阅读模式并存，且报告页更常用。

## What Changes

- **改为侧栏 + 正文**：左侧栏放筛选条件（主题／状态／结论／仅完整）与报告列表，正文区显示选中报告，与 `DocPage.vue` 的 `doc-sidebar` 模式一致。
- **放开正文宽度**：正文不再整体锁在 76ch；段落保持可读行宽（约 78ch），表格、代码块、案例图改为占满正文区。
- **页面级标题取代卡片头**：报告标题、状态与结论标签、run/date 元信息放在页面头部，不再套 `n-card-header`。
- **正文增加章节导航**：背景与目标、当前问题、实验设计、结果与分析、结论与下一步、附录，桌面端常驻右侧或左侧小目录，窄屏折叠。
- **响应式**：≥900px 侧栏常驻；<900px 侧栏变抽屉，正文占满。

## Capabilities

### New Capabilities

- `experiments-report-layout`: 实验报告页的导航结构、正文宽度策略、标题层级与响应式行为。

### Modified Capabilities

无。数据来源与 API 不变。

## Impact

- 只改 `web/src/views/management/ExperimentsPage.vue` 及其样式；可能复用 `DocPage.vue` 的侧栏样式变量。
- 不改后端接口、不改报告生成器、不改 `management/experiments/` 下的内容。
- 需要人工在浏览器核对桌面与窄屏两种宽度下的实际渲染。
