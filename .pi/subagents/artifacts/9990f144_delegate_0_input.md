# Task for delegate

你是文献+代码精读员。项目：宠物（猫）动作识别，正在设计身份-动作解耦视频 tokenizer。需要摸清 tokenizer 家族各方案的基座选择与开源情况。
只读调研，不要修改任何文件。工作目录 /Users/zhengxinyu/pet-action-recognition。

读以下材料：
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2412.13061_vidtok.txt     (VidTok, Microsoft, 开源)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2412.10958_softvqvae.txt  (SoftVQ-VAE, 连续 1D tokenizer)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2505.17011_adaptok.txt    (AdapTok, 自适应 token 预算)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2502.13967_flextok.txt    (FlexTok, Apple, 变长 token)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2602.04202_vtok.txt       (VTok, 关键帧+残差)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2505.12053_vfrtok.txt     (VFRTok, 变帧率)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/vidtok/ /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/softvqvae/ /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/adaptok/ /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/flextok/

要回答的问题（逐条给出原文/代码证据，标注文件与行号或章节号）：
1. 各方案的基座架构（backbone、token 数、量化方式：VQ / FSQ / SoftVQ / 连续 / 变长）。做一张对比表。
2. 量化方式对比：SoftVQ-VAE 与 VQ/FSQ 的区别、码本塌缩风险、对下游'聚类/线性探针'的友好度。
3. 哪些仓库可直接运行且有权重（VidTok / SoftVQ-VAE / AdapTok / FlexTok），给出关键文件路径、训练脚本、许可证。
4. VTok 的'关键帧空间特征 + 逐帧残差 token'与 TivTok 的 TIV/TV 有何异同？VTok 是否开源？
5. AdapTok 的自适应 token 预算机制怎么工作，是否值得作为 v2 增强。
6. 对我们（身份=整段视频聚合、动作=逐帧）而言，哪套基座最适合改造，理由。

输出：结构化中文简报+对比表，每条结论必须有出处（文件名+行号/章节）。不确定标注'论文/代码未说明'。不要臆测。

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