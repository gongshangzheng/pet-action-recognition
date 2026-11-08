> **状态：用户已决定废弃并归档（2026-11-08）。** 本方案未完成；原任务状态和历史证据保留，未实施的 delta 不生效，不同步至主规范。下文为历史方案。

> 历史边界：本文记录旧规则移植方案，用户验收尚未完成。当前执行以平台 house rules 和用户指示为准，本文所述三个 skill 的旧规则未启用。

## Why

CyberVerse 上游最近修订了 OpenSpec 工作流规则：任务必须按真实依赖排序，一次只推进一个可独立验证的结果；前置项受阻时暂停其依赖工作；勾选前要先核验证据，并区分"已执行"与"已通过科学或用户验收"。本项目三个 OpenSpec skill 仍是旧版，已经出现计划与事实分叉：`gdino-crop-videomaev2-evaluation` 的 3.4、3.5、4.1、4.4 在 evidence 中已有完成记录，但 tasks.md 仍未勾选，且部分勾选项把实现、执行和验收合并在一起。

## What Changes

- 在 `openspec-propose` 增加任务拆分与排序规则：一个勾选项对应一个可独立验证的结果；实现、验证、执行、报告发布、用户验收在证据不同时拆开；按真实依赖排序，编号不足以表达前置关系时显式写出前置条件。
- 在 `openspec-apply-change` 增加执行顺序规则：按依赖顺序推进；前置项受阻时暂停其依赖任务；跳过受阻项执行独立任务，须先记录独立理由并取得用户同意；每完成一项立即勾选，不累积多个未勾选的完成项。
- 在 `openspec-update-change` 增加修订规则：改写任务时拆分合并项并重排依赖；保留已完成的历史工作和证据，不为制造连续顺序而取消勾选；编号变化影响既有引用时记录到 change 的 evidence。
- 新增能力规范，把上述行为写成可验收的要求与场景。

## Capabilities

### New Capabilities

- `openspec-workflow`: 变更任务粒度、依赖排序、受阻处理与勾选证据的行为契约。

### Modified Capabilities

无。本次只修订工作流 skill 与任务规范，不改动 `experiment-reports`、`documentation` 等既有能力的系统行为。

## Impact

- 受影响文件：`.agents/skills/openspec-propose/SKILL.md`、`.agents/skills/openspec-apply-change/SKILL.md`、`.agents/skills/openspec-update-change/SKILL.md`。
- 不受影响：项目代码、远程服务器、服务端口、数据集与训练产物。
- 后续新建或修订的 change 须按新规则编写任务；既有 change 不批量重写，只在其被修改时顺带应用，避免制造无证据的勾选变化。
- 不移植 CyberVerse 的项目专属内容：管理项目树禁用条款、worktree 路径约定和 Codex/pi 调用写法。
