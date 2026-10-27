# docs-static-build Specification

## Purpose

定义 GitHub Pages 这类「纯静态托管、无后端」场景下文档页的数据来源：构建期把 `management/docs/` 编译为静态数据，前端在生产构建读取该数据、在开发时仍走 FastAPI；并保证 history 路由的深链接可被 SPA 接管。

## Requirements

### Requirement: 构建期生成文档静态数据

构建流程 SHALL 扫描 `management/docs/` 下的 Markdown 与同名 sidecar JSON，产出前端可读取的静态数据文件；其字段 SHALL 与后端文档接口一致（列表项含 `slug/title/author/date/tags/summary/id` 以及后续新增的 `folder/order`，详情项额外含 `content` 与 `sidecar`），排序 SHALL 与后端一致。

#### Scenario: 生成列表与详情
- **WHEN** 执行构建
- **THEN** 产出静态数据文件，含全部文档的列表项与按 slug 索引的详情项，详情项的 `content` 为去掉 frontmatter 的正文

#### Scenario: 排序与后端一致
- **WHEN** 比较静态数据列表顺序与 `GET /api/management/docs` 的顺序
- **THEN** 两者一致（采用 `sync-projflow-shared-ui-docs` 扩展后的 folder 优先级 → order → id → date 降序 → slug；非法或缺失数值排后）

#### Scenario: sidecar 元数据保留
- **WHEN** 某文档存在同名 `.json`
- **THEN** 静态详情项包含该 sidecar 内容；无 sidecar 时为空对象

### Requirement: 生产构建读静态数据，开发走 FastAPI

文档取数 SHALL 通过单一来源切换层暴露：开发模式调用后端 API，生产构建读取静态数据。组件 MUST NOT 直接依赖具体来源。

#### Scenario: 本地开发
- **WHEN** 以开发模式运行前端
- **THEN** 文档列表与正文来自后端 API，改动 `management/docs/` 后刷新即可见

#### Scenario: 生产构建
- **WHEN** 以生产构建运行（如 GitHub Pages）
- **THEN** 文档列表与正文来自静态数据，无需后端

#### Scenario: 静态数据中不存在该文档
- **WHEN** 请求一个不在静态数据中的 slug
- **THEN** 取数层以错误结束（与后端 404 行为一致），页面显示空态而非崩溃

### Requirement: 生成失败必须显式失败

当 `management/docs/` 缺失、不含任何 Markdown、或 frontmatter 存在无法解析的内容时，生成步骤 SHALL 以非零退出码结束并打印可定位的错误；MUST NOT 静默产出残缺数据。

#### Scenario: 文档目录缺失
- **WHEN** 构建时仓库内没有 `management/docs/`
- **THEN** 生成步骤报错退出，构建失败

#### Scenario: frontmatter 无法解析
- **WHEN** 某篇文档的 frontmatter 含不支持的写法
- **THEN** 打印文件名与行号并退出非零

### Requirement: SPA 深链接回退

构建完成后 SHALL 提供 `404.html`（内容与 `index.html` 相同），使静态托管在直接访问 history 路由深链接时由 SPA 接管渲染。

#### Scenario: 直接访问文档深链接
- **WHEN** 浏览器直接打开 `/<repo>/management/docs/architecture`
- **THEN** 托管平台返回 `404.html`，SPA 启动后按路由渲染该文档

#### Scenario: 产物一致性
- **WHEN** 构建结束
- **THEN** `dist/404.html` 与 `dist/index.html` 内容一致

### Requirement: Static documentation metadata parity
The build SHALL generate static document list and detail data containing the metadata and deterministic ordering exposed by the local documentation API.

#### Scenario: Production document list is loaded
- **WHEN** the production application loads the static documentation list
- **THEN** its document slugs and ordering match the local API for the same repository content

### Requirement: Static documentation asset publishing
The build SHALL copy documentation `_assets` into the published static site without treating assets as documents.

#### Scenario: Documentation includes local images
- **WHEN** the documentation source contains files under `_assets`
- **THEN** the production site publishes those files at the document asset URL used by rendered Markdown

### Requirement: SPA deep-link fallback remains available
The production build SHALL publish a `404.html` whose content matches the SPA entry document.

#### Scenario: A Pages document deep link is refreshed
- **WHEN** GitHub Pages receives a request for a client-side documentation route
- **THEN** the SPA fallback can boot the application and render the requested document route
