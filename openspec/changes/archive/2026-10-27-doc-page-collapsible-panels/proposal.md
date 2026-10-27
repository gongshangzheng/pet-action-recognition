# Proposal: doc-page-collapsible-panels

## Why

管理模块的文档页面（`/management/docs`）采用三栏布局：左侧文档列表（210px，≥1024px 显示）、中间正文、右侧 TOC（180px，≥1280px 显示）。两侧栏固定占位且无法收起，在窄屏或阅读长文档/宽表格/宽代码块时，正文可用宽度被压缩，阅读体验差。

## What Changes

- 左侧文档列表支持**收起至左边缘**：收起后侧栏完全隐藏，仅保留一个贴边的展开把手，空间全部让给中间正文
- 右侧 TOC 支持**收起至右边缘**：同上，仅保留贴边展开把手
- 展开把手点击后侧栏恢复原位，恢复原有宽度与内容
- 收起状态持久化到 localStorage，刷新/重进页面保持用户偏好
- 交互模式与 `Projects.vue` 已有的进展记录折叠（collapsed + 窄条展开按钮）保持风格一致

不涉及的：
- 不改变响应式断点规则（<1024px 左栏本来就不显示，<1280px 右栏本来就不显示）
- 不改变文档导航、TOC 锚点、sidecar 弹窗等既有功能

## Capabilities

### New Capabilities

- `docs-page-layout`: 文档页面三栏布局的侧栏收起/展开行为，包括把手交互、状态持久化和与响应式断点的配合

### Modified Capabilities

（无）

## Impact

- **前端**：`web/src/views/management/DocPage.vue`（模板、script、样式）
- **后端/API**：无影响
- **依赖**：无新增依赖
