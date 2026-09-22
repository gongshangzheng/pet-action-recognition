# static-docs-for-pages

## Why

本仓库已经通过 `.github/workflows/deploy.yml` 把 `web/` 部署到 GitHub Pages（`base: '/pet-action-recognition/'`，路由为 `createWebHistory`）。但 Pages 上**没有 FastAPI 后端**，`DocPage.vue` 调 `/api/management/docs` 必然失败，文档页只能显示空态。

同时 `createWebHistory` + Pages 静态托管意味着**直接刷新深链接**（如 `/pet-action-recognition/management/docs/architecture`）会被 Pages 判为 404 —— 因为磁盘上没有该路径的文件。

目标：**不部署后端、不引数据库、不加域名**，把 `management/docs/*.md` 在构建期编译进前端产物，让文档页在 Pages 上可浏览；并补 `404.html` 让 SPA 接管深链接。

## What Changes

**1. 文档静态化**

- 新增 `web/scripts/build-docs-data.mjs`：扫描 `management/docs/` 下的 `.md` 与同名 `.json`（sidecar），产出 `web/public/docs-data.json`，字段与后端 `GET /api/management/docs`、`GET /api/management/docs/{slug}` **逐字段一致**（含 `content` 正文与 `sidecar`），排序链复刻后端。
- 新增 `web/src/api/docs.js`：文档取数的**来源切换层** —— 开发（`import.meta.env.DEV`）走 FastAPI，生产构建走静态数据。
- `web/src/views/management/DocPage.vue`：改从 `api/docs` 导入（仅一行 import 变更）。
- `web/package.json` 增加 `prebuild` 钩子调用生成脚本。
- `.gitignore` 忽略生成物 `web/public/docs-data.json`。

**2. 深链接回退**

- 新增 `web/scripts/copy-404.mjs`：把 `web/dist/index.html` 复制为 `web/dist/404.html`。
- `web/package.json` 增加 `postbuild` 钩子。

> `deploy.yml` **不需要改动** —— 它跑的是 `npm run build`，npm 会自动触发 `prebuild` / `postbuild`。

## Capabilities

### New Capabilities

- `docs-static-build`: 文档在构建期静态化、开发/生产的数据来源切换，以及 SPA 深链接的 Pages 回退。

### Modified Capabilities

（无）

## Impact

- 前端：新增 `web/scripts/build-docs-data.mjs`、`web/scripts/copy-404.mjs`、`web/src/api/docs.js`；修改 `web/src/views/management/DocPage.vue`、`web/package.json`；`.gitignore` 增一行。
- 后端：**不动**（仍提供本地开发的实时文档接口）。
- CI：`deploy.yml` 不动，但构建产物新增 `docs-data.json` 与 `404.html`。
- 行为变化：生产构建的文档页数据来自静态 JSON 而非 API；Pages 上深链接可直接刷新。
- 已知边界：Pages 上**只有文档页可用** —— 任务看板 / 项目树 / 会议 / 里程碑等仍依赖后端 API，会显示空态。本仓库文档当前 0 张图片，故不涉及 `_assets` 端点。
