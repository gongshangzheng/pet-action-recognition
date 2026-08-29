# Task for worker

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
重要环境说明：你没有 web_search 工具，必须用 bash 里的 curl/python3 直接调用公开 API 做真实检索。可用 API：(1) arXiv API: curl 'http://export.arxiv.org/api/query?search_query=...&max_results=20&sortBy=submittedDate&sortOrder=descending'（每次请求间隔 sleep 3，User-Agent 要带上）；(2) Semantic Scholar Graph API: curl 'https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,year,venue,externalIds,citationCount,abstract&limit=20'（限流时 sleep 重试）；(3) Papers with Code API: https://paperswithcode.com/api/v1/ 。禁止凭记忆编 arXiv ID——每条都必须来自 API 实际返回。返回格式：JSON 数组，字段 arxiv_id/title/year/venue/url/one_line_value_zh（一句话中文价值）。

专题E【动物/宠物动作行为识别——真实检索补全】：用 Semantic Scholar + arXiv API 检索：(1) 'animal behavior recognition video'、(2) 'dog action recognition'、'cat behavior recognition'、'pet action recognition'、(3) 'animal pose estimation' 2024-2025 新作、(4) 'livestock behavior' / 'cattle behavior recognition'（畜牧方向动作识别很活跃，方法可迁移到宠物）、(5) 'animal welfare video monitoring'。对高引条目记录 citationCount。已覆盖不要重复：DeepLabCut、SLEAP、SuperAnimal、AP-10K、APT-36K(2206.05683)、Animal Kingdom、MammalNet(2306.00576)、Keypoint-MoSeq、B-SOiD、A-SOiD、MARS、VAME、DeepEthogram、LabGym、AmadeusGPT、DANNCE、Anipose、AnimalWeb、ATRW、OpenMonkeyStudio/Challenge、JAABA、MotionMapper、MoSeq、Who Let the Dogs Out(1803.10827)、BARC、SMAL(1611.07700)、StanfordExtra。目标新增 10-20 篇。

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