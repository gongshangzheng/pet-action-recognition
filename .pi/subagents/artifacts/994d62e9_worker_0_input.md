# Task for worker

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
重要环境说明：你没有 web_search 工具，必须用 bash 里的 curl/python3 直接调用公开 API 做真实检索。可用 API：(1) arXiv API: curl 'http://export.arxiv.org/api/query?search_query=...&max_results=20&sortBy=submittedDate&sortOrder=descending'（每次请求间隔 sleep 3，User-Agent 要带上）；(2) Semantic Scholar Graph API: curl 'https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,year,venue,externalIds,citationCount,abstract&limit=20'（限流时 sleep 重试）；(3) Papers with Code API: https://paperswithcode.com/api/v1/ 。禁止凭记忆编 arXiv ID——每条都必须来自 API 实际返回。返回格式：JSON 数组，字段 arxiv_id/title/year/venue/url/one_line_value_zh（一句话中文价值）。

专题F【人类→动物迁移 & 小数据：真实检索补全】：用 Semantic Scholar + arXiv API 检索：(1) 'cross-species pose estimation'、(2) 'domain adaptation animal pose'、(3) 'transfer learning action recognition' 2023+、(4) 'few-shot action recognition' 2024-2025 最新（看 MoLo 之后的进展）、(5) 'self-supervised video pretraining small data'、(6) 'synthetic animal data' / 'animal video generation'（合成数据缓解稀缺）。并核验一篇存疑论文：是否存在名为 PoseBridge 的跨物种姿态估计域适应论文（AAAI/WACV 2022-2023 附近）——用 Semantic Scholar 搜 'PoseBridge'，如实报告找到什么。已覆盖不要重复：MAML、ProtoNet、TARN(1907.09021)、OTAM(1906.11415)、ARN、TRX(2101.06184)、HyRSM(2204.13423)、STRM(2112.05132)、MoLo(2304.00946)、Cao 2019(1908.05206)、RegDA(2103.06175)、ViTPose+、Kinetics。目标新增 8-15 篇 + PoseBridge 核验结论。

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