# Subagent Prompts

本目录集中存放当前项目所有**专用 subagent 的提示词文件**，每个 agent 一个 `.md`。

## 目录约定

```
.claude/
├── skills/             # 主 agent 使用的 skill 指南（SKILL.md + scripts/）
└── agents/             # 主 agent 通过 Agent 工具派生 subagent 时使用的提示词
    ├── README.md       # 本文件
    └── <name>.md       # 单个 subagent 的 prompt + 用法说明
```

**分工原则**：
- `skills/` 回答"主 agent 怎么做这件事"（流程、脚本、文件路径、数据 schema）
- `agents/` 回答"主 agent 把某个子任务交给专职 subagent 时，subagent 看到什么"

skill 可以**调用** agent，但 agent 的提示词**不要**内联在 SKILL.md 里（避免主上下文被写作规则污染，也避免多处引用时出现多个不一致的副本）。

## 单个 agent 文件的结构

每个 `.md` 顶部用 YAML frontmatter 声明元数据：

```yaml
---
name: <short-id>           # 短标识，用作 Agent 工具 label
role: <一句话定位>          # 这个 subagent 是干嘛的
subagent_type: general-purpose | Explore | Plan | ...   # 推荐的 subagent 类型
invoked_by: <哪个 skill 调用>
output_format: <期望的输出格式>
---
```

正文包含：
1. **输入**：主 agent 应传什么（用占位符 `<TITLE>`、`<CONTEXT>` 等）
2. **输出格式**：严格约束（"只输出字符串本身，不要前言后语"）
3. **硬性规则**：编号列表
4. **好/坏例子**：对比示范
5. **工作流程**：可选，说明 subagent 内部如何思考

## 主 agent 如何调用

skill 文档中用如下模板指引主 agent：

```markdown
调用专用 subagent（推荐）：读 `.claude/agents/<name>.md`，把文件正文作为
prompt，把 `<TITLE>`、`<CONTEXT>` 等占位符替换为实际值，通过 Agent 工具
派生一个 subagent（subagent_type 用 frontmatter 中声明的类型）。
subagent 返回后原样传给下游脚本。
```

## 新增 agent 的 checklist

- [ ] frontmatter 五项字段齐全
- [ ] 输出格式明确，主 agent 无需二次解析
- [ ] 提供至少一组好/坏例子
- [ ] 在调用方 skill 的 SKILL.md 里加引用链接
- [ ] 更新本 README 的目录约定（如有新约定）
