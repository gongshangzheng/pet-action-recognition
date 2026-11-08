# 实验证据

### 2026-11-06：规则来源核定与差异清单（tasks 1.1、1.2）

- **来源状态**：CyberVerse 工作区 `HEAD=29cb5ef`，三个 skill 的规则修订**尚未提交**，文件修改时间 2026-11-06 10:56。因此本次移植的参照是工作区内容，不是可引用的上游提交；上游提交后须按同一路径做增量核对。
- **本仓现状**：三个 skill 生成于 2026-09-07，四条规则全部缺失。`openspec-propose` 唯一的 `dependency order` 命中在第 84 行，指制品依赖顺序，与任务排序无关；`openspec-apply-change`、`openspec-update-change` 无任何命中。

待移植规则原文（逐字）：

- propose 第 138–139 行：
  - `- Make each task one independently verifiable outcome; separate implementation, validation, execution, report publication, and human acceptance when they have different completion evidence.`
  - `- Order tasks by real dependencies. Record prerequisites where numbering alone is insufficient; independent preparation is not a reason to obscure a blocking acceptance gate. Keep tasks small enough to finish and verify in one session.`
- apply-change 第 93 行（整段插入第 6 步开头）：
  - `Work through pending tasks in dependency order, one independently verifiable outcome at a time. Follow explicit prerequisites as well as numbering. If an earlier task is blocked, pause its dependent work. Only proceed to an independent task after recording why it is independent and obtaining the user's consent to skip the blocked item. Earlier completed diagnostic work remains historical evidence, not proof of later acceptance.`
- apply-change 第 99–101 行（替换原“勾选后继续”两条）：
  - `- Verify the task's acceptance evidence and record it in the change; distinguish execution from scientific or user acceptance`
  - `- Immediately mark the verified task complete in the tasks file: `- [ ]` → `- [x]``
  - `- Continue to the next unblocked dependency, rather than accumulating several unchecked completions`
- update-change 第 62–63 行：
  - `- When revising tasks, split combined outcomes into independently verifiable checkboxes, including distinct implementation, validation, execution, publication, and user acceptance when their evidence differs. Order them by real dependencies and identify prerequisites where numbering is insufficient.`
  - `- Preserve completed historical work and its evidence; do not check new tasks without supporting proof or uncheck historical results merely to make progress sequential. Keep outstanding gaps visible and record renumbering in the change evidence when it affects existing references.`

差异清单（移植 / 不移植）：

- **移植**：上述四条规则段落，共 6 行文本。
- **不移植**：调用写法改写为 `$openspec-skill (Codex) or /openspec-skill (other agents)`；CyberVerse `AGENTS.md` 的项目管理树禁用条款、worktree 兄弟目录路径约定、`avatarforcing` 等领域事实；其 `openspec-propose`、`openspec-update-change` 的 description 增补句（本项目 description 已足以触发）。
- **理由**：本次目标是任务拆分、顺序与勾选证据三条行为规则；调用写法和项目专属条款属于平台与仓库差异，整段带入会扩大审查面并与本仓既有表述冲突（见 design 决策一）。

### 2026-11-06：场景—文本映射核验（tasks 3.1–3.3）

三个 Requirement 的九个场景与 skill 文本的对应关系：

- **任务按真实依赖排序并保持单一可验证结果**
  - 一项任务混合实现与验收 → propose 规则一（实现、验证、执行、报告发布、人工验收在证据不同时拆开）与 apply 规则三（区分执行与科学或用户验收）。
  - 前置验收尚未通过 → propose 规则二（独立的前期准备不得掩盖阻塞性验收门）与 apply 规则一（前置受阻则暂停其依赖工作）。
  - 任务粒度超出单次会话 → propose 规则二末句（单次会话内可完成并核对）。
- **执行时按依赖顺序推进并立即记录证据**
  - 前置任务受阻 → apply 第 6 步段落（阻塞则暂停依赖项）。
  - 执行完成但用户验收未通过 → apply 规则三与规则四（核验证据后立即勾选，验收另计）。
  - 跳过受阻项执行独立任务 → apply 段落末句（记录独立理由并取得用户同意）。
- **修订计划时保留历史证据**
  - 修订后出现无证据的勾选 → update-change 规则二前半（无证据不勾新项）。
  - 重排任务后编号变化 → update-change 规则二后半（影响既有引用时把重排写入 evidence）。
  - 既有 change 未参与本次修订 → 由 design 决策四承载，skill 文本不重复；update-change 既有条款已要求“change 已自洽时说明并不做修改”，两者一致，记为不适用而非缺失。

文本级检查：三个 skill 无 `(Codex)`、`$openspec-`、`CyberVerse-`、`management/projects` 等上游专属写法（grep 无命中）；本仓调用写法保留，`openspec-apply-change` 2 处、`openspec-propose` 1 处 `/openspec-apply-change` 未被改写。`openspec validate --strict` 与 `git diff --check` 均通过。

### 2026-11-06：提交与剩余门禁（tasks 4.1、4.2）

- 三个 skill 与本次 change 制品在同一提交内落地，分支 `exp/sync-openspec-workflow-rules`，提交信息注明规则来源为 CyberVerse 未提交工作区。回退：`git revert` 分支 `exp/sync-openspec-workflow-rules` 上标题为 `docs: sync openspec task ordering and evidence rules` 的提交；提交号不写入本文件，因为记录提交号的修改会再次改变它。
- 工作区另有前一 change（裁剪实验）的未提交改动，本次未纳入提交，也未修改。
- 任务 4.2 为用户审阅门禁，保持未勾选；在用户确认前不宣称规则已生效。
