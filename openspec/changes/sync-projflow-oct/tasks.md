## 0. 前置：远程状态确认

- [ ] 0.1 记录同步前状态：`git fetch --all --prune`；确认 `main == origin/main`、工作区干净（当前判断：`0	0` 差异、无未提交改动，本轮无需 pull）。
- [ ] 0.2 记录上游来源 commit 清单与「不取」清单（见 proposal.md / design.md）。

## 1. LaTeX 公式支持

- [ ] 1.1 `web/package.json` 增加 `katex`、`@vscode/markdown-it-katex` 依赖并更新 lockfile。
- [ ] 1.2 `web/src/components/common/MarkdownRenderer.vue` 接入 KaTeX 插件（行内 `$…$`、块级 `$$…$$`）。
- [ ] 1.3 合并 Mermaid 配置：保持本地 `htmlLabels:false`，验证标签内公式不裁切。
- [ ] 1.4 实测三种形态：块级公式、行内公式、Mermaid 标签内公式。

## 2. article-note skill

- [ ] 2.1 取上游 `article-note` skill 全套（SKILL.md + phases + references + scripts + subagents）到 `.agents/skills/article-note/`。
- [ ] 2.2 取其 LaTeX 增补（`4b7694b` 对 phases/5-writing、subagents/methodology、scripts/validate-note.py 的改动）。
- [ ] 2.3 核对脚本 import 与目录路径按本库布局可用（`python3 -c "import ast; ..."` 语法检查）。

## 3. documentation skill 增量

- [ ] 3.1 取 `scripts/docs_order.py`。
- [ ] 3.2 在本地 SKILL.md 中增量补：LaTeX 公式写作约定、目录/排序/sidecar 约定、`docs_order.py` 调用时机（不覆盖本地章节体系）。
- [ ] 3.3 交叉检查既有写作约定无重复段落。

## 4. 菜单可配置隐藏

- [ ] 4.1 新增 `web/src/config/hidden.js`（`HIDDEN_KEYS` 默认空 + `filterHidden`），可用 key 注释按本库菜单重写。
- [ ] 4.2 `web/src/layouts/MainLayout.vue` 改用 `visibleMenuOptions`；保留本地 `live`、`evaluation/*`、`training/datasets` 等菜单项与 `keep-alive`。
- [ ] 4.3 顺带对齐侧边栏折叠持久化 key 为通用 `app.sidebar-collapsed`（旧 key 兼容读取）。
- [ ] 4.4 冒烟：临时隐藏 `papers` 组验证，再还原。

## 5. 文档登记表

- [ ] 5.1 新增 `openspec/registry.md`，取上游表结构与规则，文档行按本库 `management/docs/` 实际内容重写。
- [ ] 5.2 与文档列表接口输出比对 slug 集合，确认无遗漏/多余。

## 6. 静态托管图片 URL

- [ ] 6.1 `web/src/api/docs.js` 增加静态模式下 `/api/management/docs-assets/` → `${BASE_URL}docs-assets/` 重写。
- [ ] 6.2 生产构建产物中确认图片路径可解析，开发模式不受影响。

## 7. 验证与交付

- [ ] 7.1 `cd web && npm install && npm run build` 通过。
- [ ] 7.2 `python3 -c "import server.main"` 通过；起服务冒烟首页/文档/项目树/Live/训练。
- [ ] 7.3 `openspec validate sync-projflow-oct --strict`、`git diff --check` 通过。
- [ ] 7.4 提交（commit message 注明 ProjFlow 来源 commit），推送 `origin/main`。
