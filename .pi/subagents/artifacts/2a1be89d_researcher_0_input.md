# Task for researcher

背景：我们在做宠物（猫狗等四足动物）视频动作识别研究平台，论文库需要收录该方向文献。请调研并返回论文清单。返回格式要求：JSON 数组，每篇含 arxiv_id（尽量精确到如 2301.12345，没有 arXiv 的给空字符串）、title、year、venue、url、one_line_value_zh（一句话中文价值说明，说明它与视频动作识别的关系）。只要真实存在、可核验的论文，宁缺毋滥。优先 2022-2025 的前沿工作，兼顾奠基性经典。

你的专题：【两大核心问题】。(1) 动物动作数据稀缺：few-shot / 小样本动作识别、自监督预训练缓解数据不足、动物数据合成/增广；(2) 人类动作识别能力迁移到动物：cross-domain / cross-species 迁移学习、domain adaptation（人体姿态到动物姿态，如 PoseBridge、跨物种关键点迁移）、用人类视频基础模型微调到动物场景的有效性证据。每个子问题目标 8-15 篇，并在 JSON 之后附 5-10 行中文综合判断：这两条路线哪条更有希望、推荐怎么做。

---
**Output:**
Write your findings to exactly this path: /Users/zhengxinyu/pet-action-recognition/.pi/subagents/artifacts/outputs/2a1be89d/research.md
This path is authoritative for this run.
Ignore any other output filename or output path mentioned elsewhere, including output destinations in the base agent prompt, system prompt, or task instructions.

## Acceptance Contract
Acceptance level: attested
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Return concrete findings with file paths and severity when applicable

Required evidence: review-findings, residual-risks

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
`criteriaSatisfied[].status` must be exactly one of: satisfied, not-satisfied, not-applicable.
`commandsRun[].result` must be exactly one of: passed, failed, not-run.
`manualNotes` and `notes` are optional strings; an empty string means no note and does not satisfy `manual-notes` evidence.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```