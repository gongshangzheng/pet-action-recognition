## Why

上游 ProjFlow 自上次同步（`caac7df` 主题色/favicon/折叠、`b4552d4` 文档静态化/滚动记忆、`a025ff4` Pages 部署、`bafbe23` 侧栏折叠）之后，又落地了若干共享能力：文档正文 LaTeX 公式、`article-note` 论文笔记流水线 skill、`docs_order.py` 排序工具、菜单可配置隐藏（`HIDDEN_KEYS`）、`openspec/registry.md` 文档登记表、静态托管下文档图片 URL 重写。

本库（pet-action-recognition）当前缺这些共享能力；同时上游存在与本地领域诉求冲突的改动（暂停项目树），不能整体追随。需要一次**逐项甄别**的定向同步，而不是 blanket merge。

## What Changes

- 文档正文支持 LaTeX（KaTeX）：`web/package.json` 增依赖，`MarkdownRenderer.vue` 接入 `@vscode/markdown-it-katex`，并修好 Mermaid 标签内公式显示。
- 移植 `article-note` skill（论文精读笔记流水线：素材 → 分析 → 结构审批 → markdown 笔记），含其 LaTeX 约定。
- 文档 skill 增量补齐：`docs_order.py` 排序工具 + 目录/排序/sidecar 写作约定（不整体覆盖本地已分叉的 402 行 documentation skill）。
- 新增菜单可配置隐藏：`web/src/config/hidden.js`（`HIDDEN_KEYS` / `filterHidden`），`MainLayout.vue` 改用 `visibleMenuOptions`；保留本库领域菜单项。
- 引入 `openspec/registry.md` 文档登记表，并按本库文档现状补行。
- 静态托管场景下把正文里的 `/api/management/docs-assets/…` 重写为构建产物路径（`web/src/api/docs.js`）。
- **不取**：`e081100 chore: 暂停项目树功能及相关 skill 操作`（本库仍依赖项目树/任务看板）；上游通用版 `AGENTS.md` / `README.md` / `server/config.py` / 领域 router；上游 `openspec/changes/**` 历史 artifacts。

## Capabilities

### New Capabilities

- `docs-page-content`: 文档正文渲染契约扩展——数学公式（KaTeX）与 Mermaid 内公式、静态托管图片 URL 归一。
- `menu-visibility`: 菜单/功能入口的可配置隐藏（唯一控制点 `web/src/config/hidden.js`）。

### Modified Capabilities

- 无（本库主 specs 未登记文档渲染与菜单可见性；本次以 ADDED 形式首次登记）。

## Impact

- 前端：`web/package.json`、`web/src/components/common/MarkdownRenderer.vue`、`web/src/api/docs.js`、`web/src/layouts/MainLayout.vue`、新增 `web/src/config/hidden.js`。
- Skills：新增 `.agents/skills/article-note/**`；`.agents/skills/documentation/` 增量（含 `scripts/docs_order.py`）。
- 文档：新增 `openspec/registry.md`。
- 依赖：新增 `katex`、`@vscode/markdown-it-katex`（前端运行时）。
- 不动：`server/`、领域 router/view、`management/` 数据、`datasets/`、`results/`。
- 上游来源 commit：`4b7694b` `4ff70a0` `020074d` `ff49e310` `bd1c179` `8506eaf` `d68b86b` `bacb3e6` `073a94b`。
