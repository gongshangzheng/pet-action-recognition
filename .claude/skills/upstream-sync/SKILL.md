---
name: upstream-sync
description: |
  上游/下游拓扑与责任分工指南。说明上游=共享脚手架 owner、infraredComp/pet-action-recognition/DigitalTeacher=下游（嫁接上游 root 为公共祖先），以及如何把共享改进从上游传播到下游。
  触发场景：(1) 在上游改了共享脚手架想同步到下游 (2) 下游想 fetch 上游改进 (3) 判断某个改动该落在上游还是下游 (4) 理解四库的 git 历史关系
---

# 上游 / 下游拓扑与责任分工

四个全栈库（FastAPI `server/` + Vue3 `web/` + management/papers/evaluation 三模块）从同一套模板各自 `git init`，现以**上游为公共祖先**统一历史。

## 拓扑

```
        上游 (upstream)
        root 159e4aa「项目管理demo平台初始化」
              │  (嫁接为公共祖先)
   ┌──────────┼──────────┐
   ▼          ▼          ▼
infraredComp  pet-action  DigitalTeacher   (downstream, 下游)
```

- **上游**（branch `main`）：共享全栈脚手架的唯一 owner。
- **下游 = infraredComp / pet-action-recognition / DigitalTeacher**：各自 `git remote add upstream <上游URL>`，已嫁接上游 root 为历史公共祖先（`git merge-base HEAD upstream/main` = `159e4aa`）。

> 嫁接后四库提交日期非单调（上游 2026-07-10 是 infraredComp 2026-06-23 的祖先），属正常——git 允许，不影响功能。所有下游 commit SHA 已重写（force-push），旧 SHA 失效。

## 责任分工（决定一个改动该落在哪）

| 范围 | 归属 | 典型路径 |
|------|------|----------|
| 共享全栈脚手架 | **上游** | `server/main.py`(app+CORS+router 挂载)、`server/config.py`(路径常量模式)、`server/utils/file_utils.py`、`server/parsers/markdown_table.py`(含空表修复)、`server/parsers/tasks_parser.py`(看板=项目树同源派生)、parser 模式、`web/` 脚手架(vite.config/api/request.js/layouts/MainLayout.vue/router/index.js/styles/)、`start_services.sh`、`AGENTS.md` 结构、management/papers/evaluation **模块结构**、`.github/workflows` |
| 共享 skills | **上游** | 跨项目复用的 skill（management CRUD、web 开发指南、本 upstream-sync 等）；下游镜像成自己前缀版本时从上游取改进 |
| 红外压缩领域 | **infraredComp（下游）** | `benchmark/video/` 轮廓视频压缩评测、`datasets/`、`results/`、`server/routers/benchmark.py`、`web/src/views/benchmark/`、contour-video-* skills |
| 宠物动作识别领域 | **pet-action-recognition（下游）** | `evaluation/`、宠物专属 router/views、pet-action-recognition-* skills |
| 数字私教领域 | **DigitalTeacher（下游）** | `evaluation/`、`ppt/`、`research/`、数字私教专属 router/views、digital-teacher-* skills |
| 领域数据 | **各下游自管，永不进上游** | `management/`(team/daily/...)、`papers/` 数据、`data/*.db`、`datasets/` |

**铁律**：
1. 下游改了**共享脚手架**（修 parser、改 MainLayout 等）→ **必须先 port 回上游**（上游提交），再由上游传播到兄弟库；下游**不直接**互相传共享改动。
2. **领域代码 / 领域数据永不进上游**——`benchmark/`、`evaluation/`、`datasets/`、`data/*.db`、`management/` 数据各库自管。
3. 共享改进的 commit message 加 `[shared]` 前缀，便于识别与 cherry-pick。

## 传播工作流

### 下游同步上游的共享改进（推荐 cherry-pick，精准）

```bash
# 在下游库（已 add upstream remote）
git fetch upstream                       # 拉上游最新
git log upstream/main --oneline          # 找 [shared] 改进 commit
git cherry-pick <SHA>                   # 精准搬一个共享改进
# 例: git cherry-pick abc1234
```

> 慎用 `git merge upstream/main`：虽有共同祖先（159e4aa），但四库重叠文件已分叉，blanket merge 会大面积冲突。**cherry-pick 具体的 [shared] commit 更可控**。

### 取上游的「部分文件」到下游（共享件，保留 git 血缘）

当上游的一个 `[shared]` commit 里**只有一部分**是下游要的（例如 evaluation 模块：上游有通用后端 + 共享前端视图，下游只取前端视图、后端要自己定制），**不要用 `cp`**——会丢 git 血缘，下游看不出文件源自上游。用 `git checkout upstream/main -- <path>` 取：

```bash
git fetch upstream
# 只取共享的前端视图/组件（带血缘 stage 进下游），后端 evaluation.py 下游自己写
git checkout upstream/main -- web/src/views/evaluation/ web/src/components/common/VideoModal.vue web/src/api/evaluation.js
# 下游定制的后端/配置：直接在下游写，不 checkout（会被上游通用版覆盖）
#   server/routers/evaluation.py  -> 下游接领域数据源(codecs/序列/results.json)
#   server/config.py 的 OUTPUTS_DIR -> 下游指 results/video/ 而非 evaluation/outputs/
```

**判别规则**：文件内容跨库**通用**（视图/组件/api 客户端/数据模板）→ `git checkout upstream/main -- <path>` 取；文件**绑定领域数据源**（router 读 results.json、列 codecs）→ 下游自己写。`cp` 只在「两库该文件已分叉、想手动合并」时用，且务必 commit message 注明源自上游哪个 commit。

> 注意：`git checkout upstream/main -- <path>` 取回的文件会**覆盖**工作区同名文件（用上游版本替换），所以只对「下游该文件应等于上游」的路径用；对已定制分叉的路径别用，否则丢下游定制。

### 下游改了共享脚手架 → port 回上游

```bash
# 在下游：先把改动整理成 [shared] commit
git add server/parsers/markdown_table.py
git commit -m "[shared] fix: parser 空表导致 tasks_parser 位置映射错位"

# port 到上游（在上游工作树里应用同一 patch，或 cherry-pick 下游的 commit）
cd <上游工作树>
git cherry-pick <下游的 [shared] commit SHA>   # 下游 SHA 在上游重写后可见吗?——
# 注意：下游 commit 的 SHA 是嫁接后重写的，上游没有这些对象。
# 实操：在下游 git format-patch -1 HEAD，到上游 git am <patch>。
git format-patch -1 HEAD --stdout > /tmp/shared.patch   # 在下游
# (切到上游) git am < /tmp/shared.patch
```

上游落地后，再由各兄弟下游 `git fetch upstream && git cherry-pick <上游SHA>` 取回——形成"下游发现 → port 回上游 → 传播到所有下游"的闭环。

### 判断改动归属的快速决策

- 改的是 `server/main.py` / `config.py` / `file_utils.py` / `markdown_table.py` / `web/layouts/MainLayout.vue` / `start_services.sh` / 通用 skill？→ **上游**。
- 改的是 `benchmark/` / `evaluation/` / 领域 router/view / 领域 skill？→ **对应下游**。
- 改的是 `management/` 数据 / `papers/` / `data/*.db` / `datasets/`？→ **下游本地，不进任何远程共享**。

## 禁忌

- ❌ 下游间直接 cherry-pick 共享改动（绕过上游）。
- ❌ 把领域代码/数据推到上游（上游只放共享脚手架 + 共享 skill）。
- ❌ 在下游改共享脚手架后不 port 回上游（会导致兄弟库拿不到、长期分叉）。
- ❌ `git merge upstream/main` 不带审查（重叠文件冲突，易吞掉下游定制）。

## 经验沉淀（架构决策，供后人参考）

- **任务数据单源（2026-07-15）**：任务看板与项目树曾用两份冗余文件——`management/docs/tasks.md`（全局看板，3 段 markdown 表）+ `management/docs/projects/{slug}/tasks.json`（项目树，层级 JSON），schema 各异、手动双写易分叉。已合并为**单源 = per-project `tasks.json`**：看板（`server/parsers/tasks_parser.parse_tasks(slug)`）递归展平树 + 按 status 映射成 3 桶（completed→completed / active→in_progress / planned·paused·blocked→pending）；`tasks.md` 删除。改一处、看板与项目树同步。脚手架改动按铁律先在上游落地 `[shared]` commit，再同构同步到 infraredComp。管理 skill 脚本（`add/update/delete/list_task.py`）改操作 `tasks.json`（`--slug --id`），成员/报表/会议/里程碑仍是 markdown（`mgmt_io` markdown helpers 保留）。
- **训练界面上游/下游边界**：上游训练 UI 是上游契约（`/run` 是 stub，models/datasets 空，待下游覆盖）。infraredComp 的训练 UX（localStorage F5 持久化、config preset 回填、3s 实时轮询曲线、auto-select-latest、withSelected 下拉稳定）已回移植到上游作为通用范本，**丢弃红外特异设计**（method canny/sobel/hed、isVideo 条件字段、imagenet 提示、λ/quality 率失真字段）。下游 infraredComp **保留** λ/quality/method 等领域字段（RD 训练脚本 `scripts/train_model.py` 需要 `--quality`/`--lambda`）。判断标准：上游表单只放通用超参（epochs/lr/batch/optimizer/device/extra_args），领域超参由下游加。

## 备份与历史

嫁接操作前已为四库各做 bundle 备份（`~/backups/pregraft-<date>/`），可 `git clone <bundle> <dir>` 完整恢复旧历史。嫁接后下游 commit SHA 全变；如需回滚，从 bundle 恢复后 `git push --force` 回旧 SHA。
