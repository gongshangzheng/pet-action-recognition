## Why

`pet` 是本项目的 GPU 远程（`pet:pet-action-recognition`，已在 `git remote -v` 中配置），但仓库级 `AGENTS.md` 只写了「训练/测试必须在 pet 上跑」和服务器产物纪律，**没有**写「代码怎么交付到 pet」。这条规则原先靠 `~/.pi/agent/AGENTS.md` 的全局条目兜着；该全局条目已于 2026-10-30 移除（它误伤了只有 `origin` 的仓库），因此本仓库现在存在**规则真空**：Agent 可能用 `rsync`/`scp` 覆盖远程工作区，或在本地跑完只口头通知而不校验远程 commit。

## What Changes

- `AGENTS.md` 的「### Git 工作流」下新增「#### 交付到 pet」小节，四条规则：
  1. 代码只走 Git：`commit` → `git push pet <branch>` → 在远程显式 checkout/校验 commit（`git rev-parse` 对齐），确认后再启动服务。
  2. 禁止 `rsync` / `scp` 把本地工作区文件同步到远程部署目录；需要验证未部署分支时用 `git worktree add --detach` 在远程物化。
  3. 远程一次性脚本与临时产物只放 `tmp/`（gitignored），不放 `$HOME` 根目录，也不放系统 `/tmp`（与现有「服务器/产物纪律」第 1、2 条一致）。
  4. 本地不跑训练/测试/推理（重申现有规则），且不给远程硬编码 IP/密钥，连接细节留在 `~/.ssh/config`。
- 只改文档，不动任何代码、脚本、服务。

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
（无：纯文档补全，不改变可观察行为；`.openspec.yaml` 已设 `skip_specs: true`）

## Impact

- 文件：`AGENTS.md`（新增约 8 行）。
- 无代码、无依赖、无服务变更。
- 与 `~/code/CyberVerse/AGENTS.md`（第 15、121-123 行）保持同一套交付语义，便于两个仓库之间迁移时认知一致。
