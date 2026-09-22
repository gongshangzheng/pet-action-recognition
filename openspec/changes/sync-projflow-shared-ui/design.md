## Context

- 本仓库从 ProjFlow 派生，`web/` 与共享 skill 属上游所有。上游近期在 `web/` 落了主题色 / favicon / 折叠三批改进。
- 已确认的差异（`diff -u` 实测）：
  - `web/src/App.vue`：上游 `themeOverrides` 是 `computed` + `accentThemeOverrides`，本仓库仍是 `primaryColor: '#4f46e5'` 静态常量。
  - `web/src/stores/theme.js`：本仓库只有 `mode`，且存储键是 **`pet-action-recognition-theme`**（带仓库前缀）——上游用 `projflow-theme`。
  - `web/src/styles/{index,variables}.scss`：本仓库仍是靛蓝兜底色值、无 `--color-primary-border`。
  - `web/src/layouts/MainLayout.vue`：本仓库 `const collapsed = ref(false)`（无持久化）、`collapsed-width: 64`、`collapsed-icon-size: 22`、顶栏只有明暗切换按钮。菜单项与 logo 文案已本地分叉（数据集/实时视频流/训练体系；「宠物动作识别」/`PAR`）。
  - `web/src/views/management/DocPage.vue`：折叠条 `28px`、标签 `11px/字距 2px`。
  - `web/public/favicon.svg`：与上游改造前**同一个紫色生成器产物**（同 9522 字节，`#863bff`）。
  - `web/public/icons.svg`：未被任何代码引用的死文件。
  - `AGENTS.md` 目录树：本仓库根目录**确实有** `docs/`（原始设计文档），因此该条目正确，不需删除。
- 本仓库 `web/node_modules` 无 `yaml` 等额外依赖需求（本 change 不引入依赖）。

## Goals / Non-Goals

**Goals:**

- 三批改进与上游行为一致（除下述刻意保留项）。
- 不破坏本仓库已有的：Pages 部署（`base: '/pet-action-recognition/'`）、文档静态化、`DocPage` 折叠面板逻辑、菜单分叉。

**Non-Goals:**

- **不改存储键前缀**：本仓库既有 `pet-action-recognition-theme` 必须保留（否则用户已保存的明暗偏好丢失）；新增键同样用该前缀（`-accent` / `-favicon`）。
- 不取上游 `644fed0` 的后端排序链与 `DOCS_FOLDER_ORDER`（涉及 `server/` 与本仓库的 `build-docs-data.mjs`，是另一批工作）。
- 不取上游 `e505269` 的文档图片端点（本仓库文档暂无图，且 `_assets` 端点属另一批）。
- 不改 `base`、`deploy.yml`、端口。
- 不动菜单分叉与 logo 文案。
- **不取上游 `4a3b964` 的「根目录不设 `docs/`」约定**：本仓库根目录 `docs/` 存放原始设计文档（docx 等），
  与 `management/docs/` 的 wiki 是刻意的两层分工，属领域结构，各库自管。

## Decisions

### D1: 存储键用本仓库前缀（`pet-action-recognition-{theme,accent,favicon}`）

- 理由：`theme` 键已存在且已有用户偏好，改名等于清空偏好；`accent`/`favicon` 新增时与既有键保持同一命名风格，便于排查。
- 备选：与上游统一成 `projflow-*` —— 破坏已有偏好且语义错误（这不是 ProjFlow），不采用。

### D2: `config/*.js` 与 `favicon.js` / `layout.js` 直接取上游文件

这三个文件不含仓库特有内容（无 base、无端口、无菜单），逐字取上游可保证后续同步零冲突。

- 例外：`layout.js` 的 `SIDEBAR_DEFAULT_COLLAPSED = true` 保留上游默认（本仓库同样希望首屏让出横向空间）。

### D3: `MainLayout.vue` 按上游 diff 逐段合入，不用 cherry-pick

菜单项与 logo 文案已分叉，`cherry-pick 0799f7e`/`1341f31` 必冲突。改按上游 diff 手工合入四段：侧边栏 props（56/18）、折叠持久化与 `watch`、顶栏弹层（主题色 + 图标）、`<style>` 里的 `logo-icon` 与弹层样式。

- 理由：冲突点正好落在本仓库的定制块附近，逐个合入比解冲突更快且不会丢定制。

### D4: `App.vue` 只替换 `themeOverrides` 那一段

保留本仓库的 `naiveTheme` computed 与 `watch(mode)` 兜底（与上游一致）。

### D5: `AGENTS.md` 的目录树修正单独一条任务

与主题无关，但它属同一批上游 `[shared]` 修正（`4a3b964`），顺手一起清掉，避免留一条已知误导。

## Risks / Trade-offs

- [`DocPage.vue` 折叠条从 28px 收到 20px 后竖排标签拥挤] → 标签同步降到 `10px / 字距 1px`；若观感不佳，回退到 22px 是一行改动。
- [`stores/theme.js` 重写幅度大（新增 favicon/accent）] → 保留 `detectInitial()` 与本仓库存储键；`toggle()` 行为不变，验证时专项检查明暗切换。
- [`index.scss` 兜底令牌与 JS 写入值不一致] → 两处都改为枪灰族，并在验证里检查无 JS 时的兜底观感。
- [与上游后续 `[shared]` 改动再次分叉] → 本 change 后 `stores/theme.js`、`MainLayout.vue` 仍会因菜单/存储键继续分叉，属预期；其余文件已与上游逐字一致，后续可 `git checkout upstream/main -- <path>` 直接取。
- [删 `icons.svg` 若有引用] → 全仓 grep 确认无引用后删除。

## Migration Plan

1. 取上游三个 config 文件与 `favicon.svg`；重写 `stores/theme.js`（改存储键前缀）；合入 `App.vue`、`MainLayout.vue`、两个 scss、`DocPage.vue`、`AGENTS.md`；删 `icons.svg`。
2. 验证：dev（`http://localhost:3000/pet-action-recognition/`）下切换强调色/图标/折叠并刷新；明暗切换取对应色值；构建通过；Pages 静态数据不受影响。
3. 提交（`[shared]`）。
4. 回滚：revert 提交；localStorage 残留键无害（有校验回落）。
