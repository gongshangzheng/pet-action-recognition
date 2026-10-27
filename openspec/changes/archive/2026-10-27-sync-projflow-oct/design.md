## 背景

上游 ProjFlow 与本库已分叉：上游没有 pet 的领域文件（`server/routers/live.py`、`web/src/views/Live.vue`、`scripts/pet_*`、`models/mmaction2` 等），本库又在文档/主题链路上做过本地化改造。因此同步策略沿用 `upstream-sync` skill 的**逐项取用**，不做 `git merge upstream/main`。

## 取用方式（按文件类型分流）

| 类型 | 方式 | 适用对象 |
|------|------|----------|
| 纯新增、本地无对应 | `git checkout upstream/main -- <path>` | `.agents/skills/article-note/**`、`.agents/skills/documentation/scripts/docs_order.py`、`web/src/config/hidden.js` |
| 本地已分叉 | 手工增量改（只搬新增段落，不覆盖本地定制） | `web/src/components/common/MarkdownRenderer.vue`、`web/src/layouts/MainLayout.vue`、`web/src/api/docs.js`、`.agents/skills/documentation/SKILL.md`、`web/package.json` |
| 本地已有等价实现 | 跳过 | 滚动记忆、文内锚点、排序链、Unicode slug、静态构建、Pages 部署、折叠持久化、强调色/favicon |
| 与本地领域冲突 | 不取并记录 | `e081100` 暂停项目树、上游通用 `AGENTS.md`/`README.md`/`config.py`/领域 router、上游 `openspec/changes/**` |

## 关键决策

### D1. 不整体覆盖本地 documentation skill

本地 `.agents/skills/documentation/SKILL.md`（402 行）已按本库「双层 OpenSpec 流程 + §0–§7 编号」重写，上游版本（371 行）走了「doc-writing 合并 / docs-math 拆分」另一条演进路线。整体取上游会丢本地章节体系。**只增量补**：LaTeX 公式写作约定、目录/排序/sidecar 约定、`docs_order.py` 工具及其调用时机。

### D2. LaTeX 用 KaTeX 而非自研解析

上游 `4b7694b` 采用 `markdown-it` + `@vscode/markdown-it-katex` + `katex` 依赖，同步遵循同一套，避免两库渲染结果分叉。Mermaid 图内公式需同时开启 `htmlLabels` 兼容处理——本地 `2c51cca` 已把 `htmlLabels` 设为 `false`（SVG 原生 text，解决标签裁剪），两者需合并验证：`htmlLabels:false` 下 KaTeX 输出的 HTML 节点仍可渲染，但需实测确认不被裁切。

### D3. hidden.js 保留 pet 菜单全集

上游 `hidden.js` 的 key 列表基于上游菜单（无 `live`、无 `evaluation/datasets`、无 `training/datasets`）。取用文件后需按本地 `MainLayout.vue` 的 `menuOptions` 重写注释里的可用 key 清单，`filterHidden` 逻辑保持不变。

### D4. registry.md 按本地文档重写

上游 `openspec/registry.md` 登记的是上游文档清单（含 `projflow` 专属条目与 `notes/*`）。本库取其**表结构与规则**，文档行按 `management/docs/` 实际内容重写；已验证本库现有文档 slug 与 section 归属。

### D5. 跳过「暂停项目树」

上游 `e081100` 把项目树（`/management/projects`）及相关 skill 操作停用、菜单默认隐藏。本库的项目树与 `management/projects/*/tasks.json` 单源看板是活跃功能，**不采纳**。若将来要停用，另开 change。

### D6. `.agents` / `.claude` 目录形态不在本 change 内调整

本库 `.agents` 是指向 `.claude` 的符号链接；上游已改为 `.agents/skills` 真实目录 + `.claude/skills` 符号链接（`db9fdf8`）。本 change 只保证文件内容同步，**目录形态是否翻转另开 change 讨论**（与 `.pi` 冗余清理一起做）。

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| KaTeX 体积与新依赖影响构建 | 只在前端构建期引入；`npm run build` 通过后再合并 |
| `htmlLabels:false` 与 KaTeX HTML 输出冲突（公式显示为源码/被裁） | 手工在文档页实测块级 `$$`、行内 `$`、Mermaid 标签内公式三种形态 |
| MarkdownRenderer 手工增量改漏行 | 改完 `git diff` 逐段核对，只保留 LaTeX/资产 URL 相关新增 |
| 菜单隐藏误删领域入口 | 默认 `HIDDEN_KEYS = []`，只提供开关；改后启动服务逐项点开菜单核对 |
| registry.md 与本地文档不一致 | 按 `management/docs/` 实际文件生成行，并跑一次文档列表接口比对 |

## 验证

1. `cd web && npm install && npm run build` 通过。
2. 后端 `python3 -c "import server.main"` 无报错；`bash start_services.sh` 后首页、文档页、项目树、Live 均可打开。
3. 文档页渲染三种公式形态正确；`/api/management/docs-assets/` 图片在开发模式与静态产物下都不 404。
4. 临时把 `'papers'` 加进 `HIDDEN_KEYS`，确认整组消失、其余菜单不变，再还原。
5. `openspec validate sync-projflow-oct --strict` 通过；`git diff --check` 干净。
