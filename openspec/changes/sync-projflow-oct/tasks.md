## 0. 前置：远程状态确认

- [x] 0.1 记录同步前状态：`git fetch --all --prune` 已执行；工作区干净（开工前）。**与 proposal 的判断不同**：`main` 领先 `origin/main` 112 个提交（本轮之前的本地工作未推 GitHub），`upstream/main` 落后于本库 HEAD 主题线，无需 pull；交付时统一 push `origin/main`。
- [x] 0.2 记录上游来源 commit 清单与「不取」清单：取自 `4b7694b`（LaTeX）、`d68b86b`（技能 LaTeX 约定）、`bacb3e6`/`073a94b`（文档写作技能重组，本库只取写作约定增量）、`020074f`（docs_order）、`ff49e310`（HIDDEN_KEYS）、`bd1c179`（registry.md）、`8506eaf`（静态资产）；**不取** `e081100`（暂停项目树）、上游通用 `AGENTS.md`/`README.md`/`server/*`/领域 router、上游 `openspec/changes/**`。

## 1. LaTeX 公式支持

- [x] 1.1 `web/package.json` 增加 `katex@^0.16.47`、`@vscode/markdown-it-katex@^1.1.2` 依赖并更新 lockfile（`npm install` 实测装到 katex 0.16.47，与 mermaid 的 ^0.16 同范围，未出现多份副本）。注意：本库 `.gitignore` 明确忽略 `web/package-lock.json`（第 58 行），lockfile 更新只在本地生效，不入 Git。
- [x] 1.2 `web/src/components/common/MarkdownRenderer.vue` 接入 KaTeX 插件（行内 `$…$`、块级 `$$…$$`）：含 CJS 互操作归一化 + 美元符号守卫（内容首尾空白不进公式），并引 `katex/dist/katex.min.css`。本库文件另有链接/figure 定制，故按 hunk 增量合入而非整文件替换。
- [x] 1.3 合并 Mermaid 配置：本地 `flowchart.htmlLabels:false` 与字体同步逻辑保持不变；katex.min.css 同时为 Mermaid 图内 `$$…$$` 提供样式。
- [x] 1.4 实测三种形态：`results/tests/katex_probe/probe.mjs` 探针（复刻渲染器逻辑）覆盖行内公式、块级公式、金额 `$5 到 $10` 不被吞、代码块内 `$x$` 不解析 → 4/4 通过；构建产物含 KaTeX 字体与 `MarkdownRenderer-*.css` 中的 KaTeX 样式。Mermaid 标签内公式依赖同一份 CSS，未单独截图核对（人工过目项）。

## 2. article-note skill

- [x] 2.1 取上游 `article-note` skill 全套（22 个文件）到 `.claude/skills/article-note/`（`.agents` 是 `.claude` 的符号链接，写一处即两处可见；只有 `.claude/skills` 进 Git）。
- [x] 2.2 LaTeX 增补已包含在整套文件内（取的是含 `4b7694b` 之后的上游 HEAD 版本）：公式改为「直接用 LaTeX，仍配符号表」，`validate-note.py` 的告警改为「发现不支持的 `\(...\)` / `\[...\]`」。
- [x] 2.3 6 个脚本全部 `ast.parse` 通过；脚本只依赖标准库与可选 `requests`/`Pillow`；`.cache/article-note/` 工作区已加入 `.gitignore`；`management/docs/notes/` 由首次产笔记时创建（后端文档列表递归扫描，slug 形如 `notes/<slug>`）。

## 3. documentation skill 增量

- [x] 3.1 `scripts/docs_order.py`（509 行，仅标准库）已就位：`.claude/skills/documentation/scripts/docs_order.py`；`list management/docs` 实测可读出 11 篇文档顺序。
- [x] 3.2 本地 SKILL.md 增量补三节（不改既有章节体系）：`2.4 图片与图题`、`2.5 公式（LaTeX）`、`2.6 文档顺序工具（order）`；`2.1 文件规范` 补 `order` 字段与后端排序链 `folder → order → id → date(desc) → slug`。本地独有的「对外报告」等章节未动。
- [x] 3.3 交叉检查：IMAGE/公式/排序三节在本地 SKILL.md 原无对应内容（无重复）；上游 `doc-writing` 合并版的门禁段落未引入，避免与本地 `1.x` 双层流程章节重复。

## 4. 菜单可配置隐藏

- [x] 4.1 `web/src/config/hidden.js` 新增：`HIDDEN_KEYS` 默认空、`filterHidden` 不修改入参；注释中的可用 key 按本库菜单重写（management/papers/evaluation/datasets/training 五组 + `/live`）。
- [x] 4.2 `MainLayout.vue` 改用 `visibleMenuOptions`（`computed(() => filterHidden(menuOptions, HIDDEN_KEYS))`）；本地 `/live`、`evaluation/*`、`training/*`、`/datasets` 菜单项与 `keep-alive` 名单全部保留。
- [x] 4.3 侧边栏折叠 key 改为 `app.sidebar-collapsed`，旧 key `pet-action-recognition-sidebar-collapsed` 作为兼容读取回退。
- [x] 4.4 冒烟：`results/tests/katex_probe/hidden_probe.mjs` 覆盖「默认全显示 / 隐藏单叶子 / 隐藏整组 / 叶子全隐自动摘组 / 入参不被修改」5 项，全通过；配置文件本身保持空数组（未提交任何临时隐藏）。

## 5. 文档登记表

- [x] 5.1 新增 `openspec/registry.md`：11 篇文档逐行重写（编号 1–11 + 职责边界 + 单篇 Change 指向），类目行 `papers/docs/*`、`notes/*`；引用核对改为调用本库 `scripts/checks/check_doc_refs.py`（上游的「N 号」引用格式本库不使用）。
- [x] 5.2 与 `GET /api/management/docs` 比对：接口返回 11 篇，slug 集合与登记表逐行一致（`repo-inventory/datasets/models/training-guide/live-module/architecture/identity-and-retrieval/action-model-design/lessons/third-party-notes/handover-guide`），无遗漏无多余。

## 6. 静态托管图片 URL

- [x] 6.1 `web/src/api/docs.js` 静态分支加 `toStaticAssetUrls`：正文里 `/api/management/docs-assets/` → `${BASE_URL}docs-assets/`；源 Markdown 不改写（开发态仍走后端端点）。`MarkdownRenderer` 原有的相对 `_assets/` 改写保留。
- [x] 6.2 `build-docs-data.mjs` 的 `copyAssets` 改为「先清空目标 + 跳过点文件 + 返回资产数」，`docs-data.json` 新增 `assetCount`；`web/public/docs-assets/` 进 `.gitignore`。构建实测：11 篇文档、`assetCount 0`（本库 `_assets/` 目前无图片），产物含 KaTeX 字体；开发态走 `/api/management/docs-assets/` 不变。

## 7. 验证与交付

- [x] 7.1 `cd web && npm install && npm run build` 通过（vite 8，产出 `dist/` + `404.html`）。
- [x] 7.2 `python3 -c "import server.main"` 通过；dev server（base `/pet-action-recognition/`）实测：`/src/config/hidden.js` 可编译、`MarkdownRenderer.vue` 编译产物含 KaTeX（11 处引用）、`/management/docs/architecture` 路由 200、后端 `/api/management/docs` 返回 11 篇。页面级人工过目（LaTeX/Mermaid 肉眼核对）仍待用户确认。
- [x] 7.3 `openspec validate sync-projflow-oct --strict` 通过；`git diff --check` 无输出（无空白错误）；`scripts/checks/check_doc_refs.py` 悬空 0。
- [x] 7.4 提交并推送：commit message 注明 ProjFlow 来源 commit；push `origin/main`（本库领先的既有提交一并推送）。
