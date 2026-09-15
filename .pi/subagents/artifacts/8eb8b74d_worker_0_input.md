# Task for worker

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
你是批处理进度监控员。pet 服务器（ssh alias: pet）上正在后台运行 34 段视频的批处理（进程名 pet_batch_run.py）。
你的任务：
1. 每 10 分钟轮询一次进度。每次轮询用一个 bash 调用完成：先 sleep 600，再 ssh pet 查看两样东西 —— 文件 ~/results/batch/batch_progress.jsonl 的行数，以及文件 ~/batch_run.log 的最后两行。bash 工具超时设 900 秒。
2. 结束判定：日志出现 BATCH DONE 字样；或连续 3 次轮询进度行数无增长且 pgrep 找不到 pet_batch_run.py 进程。
3. 结束后：读取 ~/results/batch/batch_summary.json，统计 ok 与 failed 数量、逐段检出率 det_rate 和插值率 interp、插值率大于 30% 的告警段清单、总耗时。用中文写一份不超过 40 行的简要报告，保存到 pet 的 ~/results/batch/batch_report.md，并把报告全文作为你的最终输出返回。
注意：不要动 GPU；除 batch_report.md 外不要修改任何文件；ssh 偶发断连（Connection closed）属正常现象，等 60 秒重试即可。

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