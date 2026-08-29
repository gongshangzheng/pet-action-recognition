# Task for researcher

背景：我们在做宠物（猫狗等四足动物）视频动作识别研究平台，论文库需要收录该方向文献。请调研并返回论文清单。返回格式要求：JSON 数组，每篇含 arxiv_id（尽量精确到如 2301.12345，没有 arXiv 的给空字符串）、title、year、venue、url、one_line_value_zh（一句话中文价值说明，说明它与视频动作识别的关系）。只要真实存在、可核验的论文，宁缺毋滥。优先 2022-2025 的前沿工作，兼顾奠基性经典。

你的专题：【视频动作识别前沿方法】。调研 2022-2025 年比 VideoMAE 更新/更好的视频动作识别与视频理解模型，例如（不限于）：VideoMAE v2、InternVideo / InternVideo2、VideoPrism、UniFormerV2、AIM、V-JEPA / V-JEPA 2、VideoMamba/Mamba 系、多模态大模型视频理解（如 Video-LLaMA、Qwen-VL 视频类）、以及其他近两年的 SOTA。同时覆盖关键动作识别数据集新工作（Kinetics 后续、SSv2 相关）。目标 15-25 篇。

---
**Output:**
Write your findings to exactly this path: /Users/zhengxinyu/pet-action-recognition/.pi/subagents/artifacts/outputs/2890f875/research.md
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