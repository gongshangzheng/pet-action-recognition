## Context

动机见 [proposal.md](proposal.md)。当前状态：本项目三个 OpenSpec skill 生成于 2026-09-07，规则只有"勾选任务、进入下一项"；CyberVerse 已在工作区修订同样的三个 skill，但那条修订尚未提交（其 HEAD `29cb5ef` 仍是旧规则）。因此本次移植的事实来源是 CyberVerse 的工作区文件，而不是某个可引用的上游提交。

约束：本项目要求 Plan → Review → Apply，skill 文本本身即工作流契约；改动只涉及三个 Markdown 文件，不触及代码、远程仓库和服务。

## Goals / Non-Goals

**Goals**

- 三个 skill 的规则与本项目已审定的行为规范一致，且不引入 CyberVerse 的项目专属内容。
- 后续 change 的任务拆分、排序、勾选有明确可引用的判据。

**Non-Goals**

- 不批量重写既有 change 的 tasks.md。
- 不改 OpenSpec CLI、schema 或 `.openspec.yaml` 机制。
- 不引入自动化校验脚本；本次只改文本契约。

## Decisions

### 只移植规则段落，不整文件覆盖

按 [spec.md](specs/openspec-workflow/spec.md) 的要求逐段插入到现有 skill，保留本项目已有的调用写法（`/openspec-apply-change`）和端口/仓库相关的既有表述。

**理由**：CyberVerse 版本同时改写了调用示例为 `$openspec-skill (Codex) or /openspec-skill (other agents)`，整文件覆盖会把无关措辞带进来，扩大审查面。

**替代**：整文件 `git checkout` 覆盖并逐行审查。被否定，因为本仓 skill 与上游存在其他措辞差异，无法在一次审查里可靠区分"该同步的规则"和"不该同步的写法"。

### 规则落在 skill，而非 AGENTS.md

任务粒度、依赖顺序、勾选证据三组规则写入 skill 正文，AGENTS.md 保持既有 Plan → Review → Apply 表述不变。

**理由**：AGENTS.md 已指引"写 OpenSpec 制品前先读对应 skill"，规则放在 skill 才能被执行者读到；在两处重复会分叉。

**替代**：同时写进 AGENTS.md 作为硬规则。被否定，理由是重复内容必然不同步，且本次改动足以在 skill 内自洽。

### 前置条件用文字表达，不引入新编号体系

编号仍按现有 `1.1`、`1.2` 形式，跨节依赖用一句"依赖第 N 节"或句内前置说明表达。

**理由**：现有 change 已有大量 `3.4 在第 2 节及 3.3 完成后` 这类写法，继续沿用能减少新旧 change 的格式差异。

**替代**：引入 `depends_on` 字段或图结构。被否定，因为 OpenSpec CLI 不解析该字段，写了也无校验作用。

### 既有 change 按需应用，不批量重写

只在某个既有 change 因新工作被打开时，顺带按新规则拆分和纠正该 change 的任务；本次不改 `gdino-crop-videomaev2-evaluation` 等既有任务清单。

**理由**：规范要求保留历史证据、不无证据勾选；批量重写会产生大量与本次范围无关的 diff，让审查无法判断哪些勾选有证据。

**替代**：一次性把全部活跃 change 对齐新格式。被否定，同上。

## Risks / Trade-offs

- [上游修订尚未提交，规则可能继续变化] → 本次记录移植来源为 CyberVerse 工作区 `2026-11-06 10:56` 的文件状态；上游提交后如再修订，按同一路径增量更新。
- [规则只有文字约束，执行者可能不遵守] → 在 skill 中写成祈使的 MUST/SHALL 句式，并在 spec 场景中给出可核对的后果（保持未勾选、记录阻塞原因）。
- [拆分任务增加 tasks.md 长度] → 只要求证据不同的环节拆开，同一环节的多个小步骤可合并。
- [与既有 change 的格式不一致] → 明确既有 change 不做批量重写，接受过渡期并存。

## Migration Plan

1. 提交三个 skill 的文本改动，与本次 change 的制品在同一个提交系列内。
2. 若发现措辞导致行为歧义，用独立提交修订并记录原因；回退方式为 `git revert <commit>`。
3. 不涉及远程部署；pet 上的 skill 通过既有 Git 部署流程同步，本次不主动推送。

## Open Questions

无。
