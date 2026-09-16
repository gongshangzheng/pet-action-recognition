# Proposal: chore-toplevel-cleanup

## Why

仓库根目录堆积了一批散落/残留文件，污染顶层视图：五个 2026-09-14 一次性误提交的 `*.vue`/`*.py` 副本（commit d996aec "pet-local edits"，将 pet 服务器工作区文件批量拷入根目录后入库）与正式位置（`web/src/`、`server/`、`scripts/`）的同名文件内容已经分叉，对协作者和 AI 代理构成双重事实来源——读到根目录 `live.py` 会以为它就是 Live 路由（实际是缺少摄像头源管理功能的旧变体），且存在 `import config` 命中根目录旧副本的隐患。两个 ~30MB 的 zip 虽已移出 git 跟踪（7f61991），但其二进制 blob 仍以可达对象残留在 git 历史与本地对象库中，且作为本地文件继续占据 30MB 磁盘；另有空壳 `package-lock.json`（101 字节，被 git 跟踪）、playwright MCP 临时产物、种子数据库备份、散落 `.DS_Store` 等。逐项核实结论见 design.md 决策表。

（核实更正：最初怀疑的"web 静态服务可能泄露根目录 zip"不成立——`server/main.py` 无 StaticFiles 挂载仓库根，vite 以 `web/` 为服务根。真实影响是磁盘占用与 git 历史体积/误导，而非运行时泄露。）

## What Changes

纯文件清理变更，无任何代码行为变更。逐文件处置（证据与风险评估见 design.md）：

- `git rm` 五个被跟踪的根目录旧副本（内容保留在 git 历史 d996aec，可随时恢复）：
  - `CanvasPlayer.vue` — 旧变体；现行版本在 `web/src/components/live/CanvasPlayer.vue`（含 NSpin/emits/status 等根副本没有的功能）
  - `Live.vue` — 旧变体；现行版本在 `web/src/views/Live.vue`（含源管理 modal、截屏处理等）
  - `live.py` — 旧变体；现行版本在 `server/routers/live.py`（含摄像头源 CRUD 端点）
  - `live_stream.py` — 旧变体；现行版本在 `scripts/live_stream.py`（cv2 版 + `read_frame()`）
  - `config.py` — 与 `server/config.py` **逐字节一致**（diff IDENTICAL），纯冗余
- `git rm` 根目录 `package-lock.json`（101 字节空壳 `packages:{}`；根目录无 package.json，真正前端 lock 在 `web/package-lock.json` 且已 ignore）
- 待用户确认后删除未跟踪的本地大文件（不可经 git 恢复）：
  - `remix_-派爪petra.zip`（15.3MB）— 与 `third-party/remix-petra/` 解压版文件清单一致（同名组件、cats-reacting.mp4 在位、乱码文件名吻合），推荐删除
  - `pet-videos.zip`（14.8MB）— zip 内为双层嵌套结构（含完整内嵌 `.git` 与 `__MACOSX` 元数据，407 条目），与 `third-party/pet-videos/`（277 文件平铺）**内容不一致**，默认保留、待用户裁定
  - `data/papers.db.bak-seed`（32KB 种子备份）— 已核实 `data/papers.db` 现库健康（`PRAGMA integrity_check` = ok，当日仍在写入），可删
- 保留不动（已有防护，仅补记录）：
  - `.playwright-mcp/` — playwright MCP 工具的临时产物目录，可能正在使用；`.gitignore` 已覆盖（line 62）
  - `checkpoints/` — 本地空目录（权重在远程 pet 服务器）；`/checkpoints/` 已 ignore
  - 散落 `.DS_Store`（根、papers/、web/、datasets/、management/、server/、results/、evaluation/ 等）— 未跟踪、已 ignore，批量清理本地文件即可
- `.gitignore` 补充：新增根级 `/package-lock.json` 防空壳复发；顺手移除重复的 `*.zip` 条目（现有两处）

## Capabilities

### New Capabilities

（无——本变更为纯文件清理，不引入任何新行为。）

### Modified Capabilities

（无——无任何 spec 级行为变更，已在 `.openspec.yaml` 声明 `skip_specs: true`。）

## Impact

- **涉及文件**：根目录 6 个被跟踪文件经 `git rm` 删除（每个独立 `chore: remove ...` commit，可单点 revert）；若干未跟踪本地文件经 `rm` 删除（删除前逐一用户确认）；`.gitignore` 小幅补充。
- **无代码行为变更**：已核实全仓库无任何代码/脚本/文档引用根目录这六个文件（server 全部使用 `from server.config import ...`，web 引用 `web/src/components/live/CanvasPlayer.vue`）；`bash start_services.sh` 启动的后端（uvicorn server.main:app）与前端（web/ 下的 vite）均不读取任何待删文件。
- **git 历史体积**：本次**不做**历史改写——两个 zip blob（~30MB，911b3db 引入、7f61991 删除）仍留在历史中，克隆体积不变；历史重写为破坏性操作，如需瘦身应另立专项并全员协调，本 change 仅在 design.md 记录为可选后续项。
- **回滚**：被跟踪文件删除均可通过 revert 对应 commit 恢复；未跟踪文件删除不可逆，故设置用户确认门槛。
