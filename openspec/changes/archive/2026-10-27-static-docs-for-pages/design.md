## Context

- 现有部署链：`.github/workflows/deploy.yml` → `web/` 下 `npm install` + `npm run build` → 上传 `web/dist` 到 Pages。
- `web/vite.config.js` 已设 `base: '/pet-action-recognition/'`；`web/src/router/index.js` 用 `createWebHistory(import.meta.env.BASE_URL)`，即 history 模式。
- 文档读取链：`DocPage.vue` → `api/management.js` 的 `getDocList()` / `getDocDetail(slug)` → axios `request` → `/api/management/docs[/{slug}]`。
- 后端返回结构（`server/routers/management.py`）：
  - 列表项：`slug / title / author / date / tags / summary / id`
  - 详情项：上述字段 + `content`（去 frontmatter 的正文）+ `sidecar`
  - 排序：先按 `date` 降序，再按 `id` 数值升序（非数字/缺失 → `inf`）
- `management/docs/` 现有 11 篇 Markdown + 2 个 sidecar JSON，**0 张图片**，故不涉及 `_assets` 端点。
- `web/node_modules` 无 `yaml` / `js-yaml`。

## Goals / Non-Goals

**Goals:**

- Pages 上文档页（列表 + 正文 + 侧栏 + sidecar 区块）完整可用。
- 本地开发仍走 FastAPI（改 md 刷新即见），不需要重新生成。
- 深链接可直接打开/刷新。
- CI 零改动（只靠 npm 钩子）。

**Non-Goals:**

- 不静态化其它管理模块（任务看板 / 项目树 / 会议 / 里程碑）——它们在 Pages 上仍为空态。
- 不把 `_assets` 图片端点搬到 Pages（当前无图；将来若加图，再按需扩展生成脚本）。
- 不改 `deploy.yml`、不改 `vite base`、不改后端。
- 不引入 SSR / 预渲染。

## Decisions

### D1: 用 `import.meta.env.PROD` 切换来源，不新增环境变量

开发（`vite`）→ API；生产构建（`vite build`）→ 静态数据。

- 理由：`deploy.yml` 无需注入任何 `VITE_*` 变量即可生效；本地 `npm run build && npm run preview` 也能复现 Pages 行为，便于验证。
- 备选：新增 `VITE_DOCS_STATIC=1` 手工开关 —— 需要改 workflow，且容易出现「构建了但忘记开开关」的静默失效，不采用。

### D2: 生成到 `web/public/docs-data.json`，运行时 fetch（不 import 进 bundle）

- 理由 1：**开发模式完全不依赖生成物** —— 不跑 `prebuild` 也能正常 dev（dev 走 API）。
- 理由 2：文档正文体积可观，不该进主 bundle；只有进入文档页才拉取。
- 代价：多一次网络请求；必须经 `npm run build`（钩子）而非直接 `vite build`，否则产物缺文件 → 应用侧 fetch 失败 → 文档页空态（不会白屏）。
- 备选：`import data from '../generated/docs-data.json'` —— 开发也依赖生成物、正文进 bundle，不采用。

### D3: 自写最小 frontmatter 解析子集，遇不支持写法显式失败

支持的写法（覆盖本仓库全部 11 篇）：

- `key: value` 单行；值去首尾空白、去成对引号
- 内联数组 `tags: [a, b, c]`
- 数字字面量（如 `id: 8`）转 number，与后端 YAML 行为一致
- 日期保持字符串（后端 `_normalize_date` 输出 ISO 字符串）

规则：

- 只解析头部第一个 `---` 到其后第一个 `---` 之间的内容，正文按后端同样的方式 `slice(end + 3).trim()`。
- 遇到无法识别的行（不以 `key:` 开头）→ 打印 `文件:行号 + 原文` 并以非零码退出。
- 理由：为一个一次性构建脚本引入 `yaml` devDependency 收益低；显式失败保证「要么正确、要么报错」，不会静默产出缺字段的文档。
- 备选：引入 `yaml` —— 目前不需要；若将来 frontmatter 变复杂（多行字符串、嵌套），脚本会先报错，届时再评估。

### D4: 排序复刻后端的两趟稳定排序

```js
docs.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)) // date 降序
docs.sort((a, b) => idNum(a) - idNum(b))                              // id 升序，inf 最后
```

- `idNum`：数字 → Number；非数字或缺失 → `Infinity`。
- 理由：静态数据的顺序必须与 API 一致，否则同一份文档在本地与 Pages 上侧栏顺序不同。
- 依赖：`Array.prototype.sort` 的稳定性（ES2019 起 V8 保证，Node 22 无问题）。

### D5: 404.html 由 `postbuild` 复制，`deploy.yml` 不动

`web/scripts/copy-404.mjs` 把 `dist/index.html` 复制为 `dist/404.html`。

- 理由：npm 会在 `build` 前后自动跑 `prebuild` / `postbuild`，CI 用的就是 `npm run build`，因此**无需改 workflow**（改动最小）。
- 备选：在 `deploy.yml` 里加一步 `cp` —— 能工作，但本地 `npm run build` 不会产出 404.html，验证与线上不一致，不采用。

### D6: 生成物带 `generatedAt` 便于排错，前端忽略

`docs-data.json` 顶层含 `generatedAt`（ISO 时间）。前端只读 `docs` 与 `details`。

## Risks / Trade-offs

- [Pages 上除文档页外的管理模块空白] → 属预期（无后端）；在 `proposal.md` 与 README 类说明中标注。若将来要，可按同一模式扩展。
- [直接 `vite build`（绕过 npm）导致产物无 `docs-data.json`] → 文档页显示空态、控制台报错，不会白屏；README 的构建说明强调用 `npm run build`。
- [frontmatter 出现多行/嵌套 YAML] → 脚本显式报错退出，CI 构建失败而不是发布错数据。
- [文档页首次进入多一次 fetch] → 与原先的 API 请求等价（原先也是一次 `/api/management/docs`），无回退。
- [深链接首帧是 404.html 内容再被 SPA 接管] → Pages 静态托管的固有行为，SPA 启动后路由即刻纠正；与 `index.html` 完全一致所以无闪屏差异。
- [Pages 缓存旧 JSON] → 文件名带内容无关，部署时整站替换，不额外处理。

## Migration Plan

1. 新增两个脚本与 `api/docs.js`，改 `DocPage.vue` 的 import，改 `package.json` 钩子，改 `.gitignore`。
2. 本地验证：`npm run build` → 产物含 `docs-data.json` 与 `404.html`；`npm run preview` 下文档页可读；dev 下仍走后端。
3. 提交并 push → `deploy.yml` 自动构建部署。
4. 回滚：revert 提交即可；`docs-data.json` 未入库故无残留状态。

## 归档时的后续演进说明

本文件保留首次静态化实现的设计记录。后续 `sync-projflow-shared-ui-docs` 已扩展 folder/order 元数据、目录过滤、图片资产发布及排序规则；当前规格以该后续实现为准，本 change 的 delta 已协调排序描述，避免主规格同时保留冲突的顺序要求。
