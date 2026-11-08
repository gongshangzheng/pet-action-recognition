## 1. 事实核定与规则来源冻结

- [x] 1.1 逐字记录 CyberVerse 三个 skill 中待移植的规则段落原文，以及其所在工作区状态（未提交、2026-11-06）；与本项目对应段落做差异清单，标出"移植"与"不移植"（Codex/pi 调用写法、项目管理树、worktree 路径）。
- [x] 1.2 确认本仓 skill 中不存在的规则只有本次四条：propose 的任务粒度与排序、apply 的依赖顺序与证据勾选、update-change 的拆分与历史证据保留。

## 2. 修改 skill 文本

- [x] 2.1 在 `.agents/skills/openspec-propose/SKILL.md` 增加任务拆分与依赖排序两条规则，位置在 "Artifact Creation Guidelines" 列表内，与既有条目并列。
- [x] 2.2 在 `.agents/skills/openspec-apply-change/SKILL.md` 第 6 步增加依赖顺序、受阻暂停、跳过需记录理由并征得同意、勾选前核验证据四条要求，替换原来的"勾选后继续下一项"。
- [x] 2.3 在 `.agents/skills/openspec-update-change/SKILL.md` 第 4 步增加拆分复合任务、保留历史证据、重排编号写入 evidence 三条要求。

## 3. 文本级核验

- [x] 3.1 逐条对照 `specs/openspec-workflow/spec.md` 的三个 Requirement，确认每个场景在 skill 文本中有对应的可执行表述；缺失项补写或记为不适用。
- [x] 3.2 确认三个 skill 未引入 CyberVerse 专属内容，且本仓既有调用写法（`/openspec-apply-change`）未被改写。
- [x] 3.3 运行 `openspec validate sync-openspec-workflow-rules --strict` 与 `git diff --check`，两项通过。

## 4. 交付

- [x] 4.1 与本次 change 制品一起提交，提交信息说明规则来源为 CyberVerse 未提交工作区，便于上游提交后追溯增量。
- [ ] 4.2 用户审阅改后的三个 skill，确认规则表述可执行；未确认前不宣称生效。
