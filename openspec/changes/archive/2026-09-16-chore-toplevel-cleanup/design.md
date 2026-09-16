# Design: chore-toplevel-cleanup

## Context

2026-09-16 对根目录散落文件逐项取证（git ls-files / git log --follow / git show --name-status / diff / unzip -l / sqlite3 integrity_check / 全仓引用 grep）。关键事实：

- 五个根目录 `*.vue`/`*.py` 均为 commit **d996aec**（2026-09-14 11:17 "pet-local edits … 回收进版本管理"）以 A（新增）状态一次性入库；该 commit 未触碰 `web/src/`、`server/`。时间戳同秒（Sep 14 11:19）与之吻合，判定为同一次从 pet 服务器工作区向仓库根的误拷贝。
- 根目录副本内容与正式位置**已分叉**：正式位置均为功能超集（新增摄像头源管理、NSpin/emits、cv2 读取等），且 `git log --all --find-object=<根文件blob>` 证实根副本内容从未在任何正式路径的历史中出现过——它们是独立演化的旧变体，而非正式文件的旧版本快照。
- 两个 zip 已由 commit **7f61991**（"chore: 移除入库的二进制zip…本地文件保留"）移出跟踪，`.gitignore` 已含 `*.zip`；其 blob（14.8MB + 15.3MB）仍以可达对象留存于 git 历史（911b3db 引入），`size-pack` 约 1MB 说明 blob 目前为松散对象。
- `server/main.py` 无任何 `StaticFiles`/`mount` 挂载仓库根；vite 以 `web/` 为根（`start_services.sh` 中 `cd "$BASE_DIR/web"`）。根目录文件不会被任何服务对外暴露。
- 全仓引用核查：server 代码统一 `from server.config import ...`；web 引用 `web/src/components/live/CanvasPlayer.vue`；scripts/server 引用 `scripts/live_stream.py`、`server/routers/live.py`。无任何代码、脚本、文档、workflow 引用根目录待删文件。

## Goals / Non-Goals

**Goals:**
- 根目录只保留真实属于顶层入口的文件（README、AGENTS.md、start_services.sh、openspec/ 等既有目录）
- 每个删除动作独立 commit、可单点 revert；未跟踪文件删除设用户确认门槛
- 补齐 `.gitignore` 防复发，不改变任何运行时行为

**Non-Goals:**
- 不做 git 历史改写（zip blob ~30MB 继续留在历史；如需克隆瘦身另立专项，需全员协调，破坏性操作）
- 不清理根目录 `live/` 目录（不在本次盘点清单内，且 `/live/` 已 ignore；如需处置另行立项）
- 不改动 `third-party/`、`data/papers.db` 现库及任何业务代码

## Decisions

### 逐文件去留决策表

| 文件 | 核实证据 | 处置 | 风险与回滚 |
|---|---|---|---|
| `CanvasPlayer.vue` (3.3KB) | **被跟踪**，d996aec 新增；与 `web/src/components/live/CanvasPlayer.vue` diff 不同：web 版多出 `watch`/`NSpin`/`emit(result/done/status)`/连接日志，根副本无；全仓无引用根副本 | **git rm**（独立 commit） | 低：内容永久留存于 d996aec，`git revert <commit>` 即恢复 |
| `Live.vue` (10.7KB) | **被跟踪**，d996aec 新增（`--follow` 链至 web 版早期历史，证明同源）；与 `web/src/views/Live.vue` diff 不同：web 版为功能超集（源管理 modal、截屏入库、PtzJoystick 集成），根副本停留在 `<n-button>` 旧写法；无引用 | **git rm**（独立 commit） | 低：同上，revert 可恢复 |
| `live.py` (7.5KB) | **被跟踪**，d996aec 新增；docstring 自称 "Live 路由"；与 `server/routers/live.py` diff 不同：server 版多出 sources CRUD 四个端点与 `db_live` 源管理函数导入，根副本为其子集；server 代码 `from server.config import`，无人 import 根 `live.py` | **git rm**（独立 commit） | 低：revert 可恢复；删除同时消除误 `python live.py` / 误 import 的隐患 |
| `live_stream.py` (6.2KB) | **被跟踪**，d996aec 新增；与 `scripts/live_stream.py` diff 不同：scripts 版用 cv2 + `read_frame()`（BGR→RGB），根副本用 decord 旧实现；无引用根副本 | **git rm**（独立 commit） | 低：revert 可恢复 |
| `config.py` (3.9KB) | **被跟踪**，d996aec 新增；`diff config.py server/config.py` → **IDENTICAL**（逐字节一致）；server 代码全部 `from server.config import ...`，无 `import config` 命中根副本 | **git rm**（独立 commit） | 极低：内容与 server/config.py 完全一致，零信息损失；revert 可恢复 |
| `package-lock.json` (101B) | **被跟踪**，75f0956 "Nightly auto sync" 引入；内容为空壳 `{packages:{}}`；根目录**无 package.json**；真正前端 lock 为 `web/package-lock.json`（123KB，已 ignore） | **git rm**（独立 commit） | 极低：无任何 npm 工作流消费根级 lock；revert 可恢复 |
| `remix_-派爪petra.zip` (15.3MB, r--r--r--) | **未跟踪**（7f61991 移除，`*.zip` 已 ignore）；`unzip -l` 27 条目 vs `third-party/remix-petra/` 25 文件：LiveStreamView.tsx、HomeView.tsx、cats-reacting.mp4 等同名文件在解压目录逐一对位，乱码文件名（GBK 编码痕迹）吻合 → 判定内容一致 | **删（用户确认后 `rm`）** | 中：未跟踪文件不可经 git 恢复 → 确认门槛 + 删前 `shasum` 留档；若用户否决则保留不动 |
| `pet-videos.zip` (14.8MB, r--r--r--) | **未跟踪**；zip 为双层嵌套 `pet-videos/pet-videos/`，内含完整 `.git`（401B config 等）与 `__MACOSX` 元数据，407 条目；`third-party/pet-videos/` 为 277 文件平铺结构（含 SERVER_DEPLOYMENT.md 等 zip 内没有的文件）→ **内容不一致**，非同一内容的解压版 | **默认保留不动，待用户裁定** | 低（保留无风险）；若用户确认删，同样不可恢复，删前留 shasum |
| `data/papers.db.bak-seed` (32KB) | **未跟踪**，`data/*.bak*` 已 ignore；2026-08-31 种子备份；现库 `data/papers.db`（520KB）`PRAGMA integrity_check` = ok、sqlite_master 7 对象、当日仍在写入 → **现库健康** | **删（用户确认后 `rm`）** | 低：种子数据可由 `data/extracted_papers.json` 重建；删前留 shasum；不可 git 恢复故需确认 |
| `.playwright-mcp/` (59 项) | **未跟踪**，`.gitignore:62 .playwright-mcp/` 已覆盖（`git check-ignore` 验证通过）；playwright MCP 工具可能正在读写 | **保留不动** + 已确认 .gitignore 覆盖 | 无：运行中工具的临时目录，删除可能破坏进行中的 MCP 会话 |
| `checkpoints/`（空目录） | **未跟踪**（0 文件），`/checkpoints/` 已 ignore；权重在远程 pet 服务器 | **保留不动** | 无：git 不跟踪空目录，保留作为本地挂载/输出占位无害 |
| 散落 `.DS_Store`（根、papers/、web/、datasets/、management/、management/weekly/、server/、results/、results/batch/、evaluation/ 等） | **未跟踪**，`.gitignore:46 .DS_Store` 已覆盖（验证通过）；纯 macOS Finder 元数据 | **本地 `find … -name .DS_Store -delete` 清理**（限仓库内、排除 `.git/`、排除 `web/node_modules/`）；不入 commit | 极低：系统随时再生，.gitignore 已防其入库 |

### 关键决策与备选方案

1. **五个代码副本用 `git rm` 而非 `git mv` 回正式位置** — 正式位置已存在更新版本，"移动"会造成覆盖或冲突；根副本无独有功能（正式版为超集，且 `--find-object` 证实其内容从未进入正式演化线）。备选"逐 diff 人工合并"被否：成本高且无证据表明根副本含未回收的独有修改（d996aec 提交信息自称是"回收"动作，正式文件此后仍独立演进）。
2. **删除按文件分独立 commit**（`chore: remove CanvasPlayer.vue (stale root copy)` 等 6 个）— 单点 revert 粒度；备选"一个 commit 全删"被否：package-lock 与五个副本性质不同，分开便于选择性回滚。
3. **未跟踪删除设"用户确认"前置门槛而非直接执行** — `rm` 不可逆，且 zip（r--r--r-- 只读权限）是用户手动放入的资产；确认动作放在 tasks.md 阶段 2 的显式勾选项。
4. **`.gitignore` 增量最小化**：仅新增根级 `/package-lock.json`（防空壳复发——现有条目只覆盖 `web/package-lock.json`），并移除重复的 `*.zip`（line ~62 与 line ~69 各一条，`*.zip` 已注释"2026-09-15 用户裁定"）。其余项 coverage 已完备，不加冗余规则。

## Risks / Trade-offs

- [根副本含未在正式位置出现的 pet 本地微调（无法 100% 排除）] → 五个文件均在 git 历史（d996aec）中永久可查；apply 阶段删除前逐文件 `diff` 输出留档到本 change 目录附注，若发现疑似独有修改即中止并上报用户。
- [误删用户仍需要的 zip] → 删除前置 `unzip -l` 清单 + `shasum` 留档，且必须用户逐个确认；pet-videos.zip 因内容不一致默认保留。
- [papers.db.bak-seed 删除后无种子] → 已验证现库健康 + `extracted_papers.json` 可重建种子；确认门槛兜底。
- [.playwright-mcp/ 误清理影响进行中的浏览器自动化] → 明确保留，仅在 tasks 验证阶段确认 ignore 覆盖。
- [git 历史仍携带 ~30MB zip blob] → 接受（非目标）；在 proposal/本文件记录历史改写为可选后续专项。

## Migration Plan

1. 阶段 1（取证复核）：apply 时重跑关键 diff/check-ignore 命令，与本文件决策表比对，任何不一致即停。
2. 阶段 2（执行）：6 个 `git rm` 各自独立 commit（顺序：五个副本从旧到新 → package-lock.json）；未跟踪项在用户逐个确认后 `rm`。
3. 阶段 3：`.gitignore` 补充独立 commit（`chore: gitignore root package-lock.json, dedupe *.zip`）。
4. 阶段 4（验证）：`git status` 干净（相对 HEAD）、`bash start_services.sh` 后端 `/api/health` 200 + 前端 3000 可打开、Live 页面功能正常（确认未误删在用文件）。
5. 回滚：任一 commit 单独 `git revert`；未跟踪删除无法回滚（靠确认门槛规避）。

## Open Questions

- `pet-videos.zip` 与 `remix_-派爪petra.zip` 的最终去留（尤其前者内容与 third-party/ 不一致）——需用户裁定，不阻塞五个代码副本与 package-lock 的清理。
