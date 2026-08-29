# Task for worker

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
重要环境说明：你没有 web_search 工具，必须用 bash 里的 curl/python3 直接调用公开 API 做真实检索。可用 API：(1) arXiv API: curl 'http://export.arxiv.org/api/query?search_query=...&max_results=20&sortBy=submittedDate&sortOrder=descending'（每次请求间隔 sleep 3，User-Agent 要带上）；(2) Semantic Scholar Graph API: curl 'https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,year,venue,externalIds,citationCount,abstract&limit=20'（限流时 sleep 重试）；(3) Papers with Code API: https://paperswithcode.com/api/v1/ 。禁止凭记忆编 arXiv ID——每条都必须来自 API 实际返回。返回格式：JSON 数组，字段 arxiv_id/title/year/venue/url/one_line_value_zh（一句话中文价值）。

专题D【2024-2025 动作识别最新前沿】：用 arXiv API 检索 2024 年至今的动作识别/视频理解新工作。建议查询（search_query 可组合 ti/abs/cat）：'action recognition' cat:cs.CV 按日期排序翻 2-3 页；'video foundation model'；'video understanding'；'skeleton action recognition' 2024+；'temporal action detection' 2024+。筛选标准：与视频动作识别直接相关、有一定影响力迹象（机构/引用/后续工作）。再用 Semantic Scholar 对筛出的重点条目查 citationCount 佐证。目标新增 10-20 篇我们清单外的工作（已覆盖：VideoMAE系、InternVideo系、VideoPrism、V-JEPA系、UniFormer系、AIM、VideoMamba、TimeSformer、SlowFast、MViT、Video Swin、Qwen2/2.5-VL、Video-LLaMA/LLaVA/ChatGPT、VILA——不要重复）。

## Acceptance Contract
Acceptance level: checked
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope

Required evidence: changed-files, tests-added, commands-run, residual-risks, no-staged-files

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