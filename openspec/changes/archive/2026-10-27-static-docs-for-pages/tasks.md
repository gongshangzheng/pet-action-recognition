## 1. 静态数据生成脚本

- [x] 1.1 新增 `web/scripts/build-docs-data.mjs`：定位仓库根（脚本上溯两级），校验 `management/docs/` 存在且含 ≥1 篇 `.md`，否则非零退出
- [x] 1.2 实现最小 frontmatter 解析（单行 `key: value`、内联数组、数字、去引号），无法解析的行打印 `文件:行号` 并退出
- [x] 1.3 生成列表项（`slug/title/author/date/tags/summary/id`）与详情项（+ `content`/`sidecar`），sidecar 读同名 `.json`
- [x] 1.4 复刻后端排序：`date` 降序 → `id` 数值升序（非数字/缺失为 `Infinity`）
- [x] 1.5 写出 `web/public/docs-data.json`（含 `generatedAt`、`docs`、`details`），打印条数与输出路径

## 2. 前端来源切换层

- [x] 2.1 新增 `web/src/api/docs.js`：`getDocList()` / `getDocDetail(slug)`；`import.meta.env.PROD` 时 fetch `${import.meta.env.BASE_URL}docs-data.json`，否则调用 `api/management.js`
- [x] 2.2 静态分支：slug 不存在时抛错（与后端 404 一致）；数据只拉一次并缓存
- [x] 2.3 `DocPage.vue`：import 由 `api/management` 改为 `api/docs`（其余逻辑不动）

## 3. 深链接回退

- [x] 3.1 新增 `web/scripts/copy-404.mjs`：`dist/index.html` → `dist/404.html`（缺 index.html 时报错退出）
- [x] 3.2 `web/package.json`：加 `prebuild`（生成数据）与 `postbuild`（复制 404）钩子
- [x] 3.3 `.gitignore`：忽略 `web/public/docs-data.json`

## 4. 验证

- [x] 4.1 `npm run build` 成功，产物含 `web/dist/docs-data.json` 与 `web/dist/404.html`（`404.html` 内容与 `index.html` 一致；`docs-data.json` 为文档数据）
- [x] 4.2 静态数据字段与排序对照后端：本地起后端比对 `GET /api/management/docs` 的顺序与字段
- [x] 4.3 `npm run preview`（生产构建）下文档页可见列表 + 正文 + sidecar 区块，且深链接直接打开可渲染
- [x] 4.4 开发模式（`npm run dev`）文档页仍走后端 API，改 md 刷新即见
- [x] 4.5 frontmatter 不支持写法 / `management/docs` 缺失时脚本非零退出（用临时目录演练后还原）
- [x] 4.6 `openspec validate static-docs-for-pages` 通过

## 5. 收尾

- [x] 5.1 提交（说明 Pages 上仅文档页可用的边界）
- [x] 5.2 push 后确认 `deploy.yml` 构建成功、Pages 上文档页与深链接可用
