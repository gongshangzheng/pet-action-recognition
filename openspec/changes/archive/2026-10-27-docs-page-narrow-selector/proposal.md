# Proposal: docs-page-narrow-selector

## Why

文档页在窄视口（<1024px）下用下拉选择器替代左栏文档列表。但页面根容器 `.doc-page` 固定为 `flex-direction: row`，
这个选择器就成了**横向 flex 子项**：它按内容/默认 100% 宽度抢走一大段横向空间，把正文挤成窄条，
且与正文之间还留着 `gap: 24px`。结果是最该看正文的窄屏上，正文反而最窄——纯布局缺陷，不是设计取舍。

## What Changes

- `.doc-page` 改为**窄屏纵向、宽屏横向**：<1024px 时 `flex-direction: column`，选择器独占一行、正文整宽；≥1024px 恢复三栏横向布局。
- 窄屏下收紧间距：页面 padding 24px → 16px，正文卡片内边距 24px → 16px（≤640px 时更紧），把宽度还给正文。
- 选择器在窄屏下 `width: 100%` 且取消多余的 `margin-bottom`（间距交给 flex `gap`）；下拉菜单宽度与触发器解耦（`consistent-menu-width: false`），避免弹层被拉成整屏宽。
- 断点与既有行为保持不变：≥1024px 显示左栏、隐藏选择器；≥1280px 显示右栏 TOC；两侧收起把手逻辑不动。

## Capabilities

### Modified Capabilities

- `docs-page-layout`: 新增「窄屏文档选择器独占一行、正文整宽」要求，并把「断点以下横向空间分配」写成可验收场景。

## Impact

- 仅 `web/src/views/management/DocPage.vue` 的 `<style scoped>` 与选择器模板属性；无 JS 逻辑、无接口、无数据改动。
- 该文件属**共享脚手架**（上游 ProjFlow 同源、同一处缺陷）→ 修复需先落上游 `[shared]` 提交，再回本库，符合 upstream-sync 铁律。
