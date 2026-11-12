## Context

主仓库当前位于 `main`，HEAD 为 `59111d7b77b1d9c0508849b35924b733ea86aea5`，有与本工作无关的已修改和未跟踪文件。现有父目录 `../.worktree/` 可容纳独立 worktree；启动前须重新核对 HEAD、目标路径和分支是否冲突。

## Goals / Non-Goals

在独立 worktree 中继续 `pet-pipeline`，保留现有计划与数据卡；不重写 main、不清理其他工作、不访问远程或移动运行产物。

## Decisions

候选分支 `work/pet-pipeline`，候选目录 `../.worktree/pet-pipeline`。以执行时核对的当前 HEAD 创建，保留已有提交。若目标已存在、分支已存在或 HEAD 不符，停止并报告，不覆盖。

携带范围仅为 `openspec/changes/pet-pipeline/` 中现有更改、`docs/pet-raw-data-card.md` 和 `AGENTS.md` 的数据卡入口。另将本迁移 change 自身带入新 worktree，以便留存实施证据。先逐文件核对路径、文件类型和哈希，再在新 worktree 逐字节复制；源文件不删除。`AGENTS.md` 只携带当前数据卡入口差异，若它包含其他差异则停止确认，不整文件盲目覆盖。清单外全部用户内容原样保留。

复制采用不覆盖既有不同内容的方式，记录每项来源与目标哈希，检查目标分支和源状态。主仓库相同内容会暂时存在两份；不擅自从 main 移除未提交内容。迁移失败时停止，保留源文件，不 reset、stash、clean 或强制删除。后续需要整理主仓库重复修改时另行请用户决定。

## Risks / Trade-offs

- `results/` 是独立工作区内的未跟踪运行数据，不自动出现在新 worktree。不得宣称证据文件已复制；需要时明确引用原位置，不擅自迁移。
- 主仓库和新 worktree 均有计划副本，后续只在新 worktree 更新以避免漂移。
- 不支持并行写入同一工作区；本迁移任务严格串行执行。
