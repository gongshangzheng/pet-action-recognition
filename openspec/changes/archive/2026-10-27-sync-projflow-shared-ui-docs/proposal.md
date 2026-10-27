## Why

GitHub Pages 的静态文档模式已可用，但与 ProjFlow 共享文档体验相比，仍缺少 Unicode slug、安全路径校验、稳定列表排序、图片资产、文内锚点和阅读位置恢复。这些行为必须同时适配 FastAPI 开发模式与 Pages 构建期静态数据，避免两个来源分叉。

## What Changes

- 后端文档路由支持 Unicode slug，拒绝空 slug 与路径遍历，并为文档返回 folder/order 元数据和确定性排序。
- 文档扫描跳过 `_assets` 等下划线目录，开发模式只读提供 `management/docs/_assets` 图片资源。
- 构建期文档生成器复刻 API 的元数据、排序与资产复制规则，供 GitHub Pages 使用。
- 文档页支持 hash 锚点、路由间阅读位置恢复和 Markdown 图片图题；Markdown HTML 不再直接渲染。

## Capabilities

### New Capabilities
- `docs-shared-experience`: FastAPI 与静态文档来源共用的文档定位、排序、图片和阅读体验。
- `docs-static-build`: GitHub Pages 构建期静态文档数据、资产及 history 回退。

### Modified Capabilities
- 无。

## Impact

- 后端：`server/config.py`、`server/main.py`、`server/routers/management.py`。
- 前端：文档生成脚本、Markdown 渲染器、文档页、全局样式及滚动记忆工具。
- 不增加依赖；生产 Pages 仍无需 FastAPI 后端即可浏览文档。
