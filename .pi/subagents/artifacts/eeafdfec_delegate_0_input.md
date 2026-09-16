# Task for delegate

你是文献+代码精读员。项目：宠物（猫）动作识别，正在设计身份-动作解耦视频 tokenizer；DeRA 是我们的对照方案（双流 + 显式对齐）。
只读调研，不要修改任何文件。工作目录 /Users/zhengxinyu/pet-action-recognition。

读以下材料：
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2512.04483_dera.txt   (DeRA, 2025-12)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2410.21264_larp.txt   (LARP, DeRA 的基座)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/larp/               (LARP 官方开源代码)

要回答的问题（逐条给出原文/代码证据，标注文件与行号或章节号）：
1. DeRA 的双流结构细节：appearance queries（第一帧）+ motion queries（全片段）各多少 token、共享 encoder 怎么实现（两路拼接后过同一 encoder？）、拼接后如何量化。
2. 显式对齐损失的具体形式（负余弦相似度）、对齐目标（DINOv3 图像 / InternVideo2 视频）的取特征层、MLP 投影结构、损失权重。
3. SACP（Symmetric Alignment-Conflict Projection）的算法伪代码与实现要点，梯度冲突如何检测与重加权。
4. LARP 的 1D tokenizer 基座结构（bottleneck attention、token 数、量化方式），代码里关键实现文件路径。
5. LARP 仓库的可用性：依赖、预训练权重、许可证、训练脚本（UCF-101 怎么跑）。
6. 如果我们要复现 DeRA 式的显式对齐（外观↔DINOv3，动作↔视频基础模型），从 LARP 仓库能直接复用哪些代码，缺什么。

输出：结构化中文简报，每条结论必须有出处（文件名+行号/章节）。不确定标注'论文/代码未说明'。不要臆测。

## Acceptance Contract
Acceptance level: attested
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Return a concise result and residual risks when applicable

Required evidence: manual-notes, residual-risks

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