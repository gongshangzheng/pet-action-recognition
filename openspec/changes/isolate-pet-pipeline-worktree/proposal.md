## Why

`pet-pipeline` 的近期提交和未提交计划位于主仓库 main，后续工作需要独立 worktree，同时不能丢失主仓库已有的其他修改。

## What Changes

- 从当前已核对的 main 提交创建专用分支和独立 worktree。
- 按明确清单携带本 change 所需未提交文件并核对内容，其他修改原样保留。
- 后续 `pet-pipeline` 工作在新 worktree 继续；不改写 main 历史，不清理未授权内容。

## Capabilities

### New Capabilities

无。这是工作区整理，不改变产品行为，使用 `skip_specs: true`。

### Modified Capabilities

无。

## Impact

影响本地 Git worktree、分支及经核准的未提交规划和文档；不操作远程服务器或数据产物。
