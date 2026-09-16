# Tasks: chore-toplevel-cleanup

## 1. 逐文件核实取证（apply 前置复核，与 design.md 决策表比对，不一致即停）

- [ ] 1.1 重跑 `git ls-files` + `git log --oneline --follow -- <file>` 确认五个副本（CanvasPlayer.vue / Live.vue / live.py / live_stream.py / config.py）与 package-lock.json 仍被跟踪、仍停留在 d996aec / 75f0956，无新提交改动了正式位置使决策表失效
- [ ] 1.2 重跑 `diff` 五组对比（根副本 vs web/src/components/live/CanvasPlayer.vue、web/src/views/Live.vue、server/routers/live.py、scripts/live_stream.py、server/config.py），将 diff 输出留档到本 change 目录（如 `notes/evidence-*.diff`），确认正式位置仍为超集、根副本无独有修改；发现疑似独有修改即中止并上报用户
- [ ] 1.3 `grep` 全仓复核无引用：`import config`、`python live.py`、根级 CanvasPlayer/Live.vue 引用均为零命中（web/server/scripts/docs/.github）
- [ ] 1.4 `unzip -l` 复核两个 zip 清单并与 third-party/ 目录对照（不解压），确认 remix zip 与解压版一致的判定、pet-videos zip 不一致的判定；`shasum -a 256` 两个 zip 与 papers.db.bak-seed 留档备查
- [ ] 1.5 `sqlite3 data/papers.db "PRAGMA integrity_check;"` 复核现库健康（预期 ok）
- [ ] 1.6 `git check-ignore -v` 复核 `.playwright-mcp/`、`.DS_Store`、`/checkpoints/`、`data/*.bak*` 的 ignore 覆盖均生效

## 2. 执行删除（每个动作独立 commit，可单点 revert）

- [ ] 2.1 `git rm CanvasPlayer.vue` → commit `chore: remove root CanvasPlayer.vue (stale copy of web/src/components/live/CanvasPlayer.vue)`
- [ ] 2.2 `git rm Live.vue` → commit `chore: remove root Live.vue (stale copy of web/src/views/Live.vue)`
- [ ] 2.3 `git rm live.py` → commit `chore: remove root live.py (stale copy of server/routers/live.py)`
- [ ] 2.4 `git rm live_stream.py` → commit `chore: remove root live_stream.py (stale copy of scripts/live_stream.py)`
- [ ] 2.5 `git rm config.py` → commit `chore: remove root config.py (byte-identical duplicate of server/config.py)`
- [ ] 2.6 `git rm package-lock.json` → commit `chore: remove empty stub root package-lock.json`
- [ ] 2.7 【用户确认】逐个确认后 `rm remix_-派爪petra.zip`（与 third-party/remix-petra/ 内容一致的判定已成立）
- [ ] 2.8 【用户确认】pet-videos.zip 去留裁定（与 third-party/pet-videos/ 内容不一致，默认保留；用户明确同意后才 `rm`）
- [ ] 2.9 【用户确认】确认现库健康后 `rm data/papers.db.bak-seed`
- [ ] 2.10 `find . -path ./.git -prune -o -path ./web/node_modules -prune -o -name ".DS_Store" -type f -print` 列出并删除仓库内散落 .DS_Store（不入 commit）

## 3. .gitignore 补充

- [ ] 3.1 新增根级 `/package-lock.json` 条目（防空壳复发；现有条目仅覆盖 web/package-lock.json）
- [ ] 3.2 移除重复的 `*.zip` 条目（保留带「2026-09-15 用户裁定」注释的那条）
- [ ] 3.3 commit `chore: gitignore root package-lock.json, dedupe *.zip entry`

## 4. 验证

- [ ] 4.1 `git status` 干净：工作区无未预期改动、无待删文件残留（.playwright-mcp/、checkpoints/ 等已 ignore 项除外）
- [ ] 4.2 `ls` 根目录复核：六个被跟踪散落文件均消失，README/AGENTS.md/start_services.sh 等顶层入口文件完好
- [ ] 4.3 `bash start_services.sh`：后端 8788 `/api/health` 返回正常、前端 3000 可访问（验证删除未破坏服务）
- [ ] 4.4 浏览器打开 web 页面并进入 Live 页：播放/推理入口正常（确认未误删在用文件）
- [ ] 4.5 验证后停止服务进程，`git log --oneline` 复核 7 个 chore commit 依次在案、每个可独立 `git revert`
