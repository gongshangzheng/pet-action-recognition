# Task for delegate

你是文献+代码精读员。项目：宠物（猫）动作识别，正在设计一个身份-动作解耦的视频 tokenizer。
只读调研，不要修改任何文件。工作目录 /Users/zhengxinyu/pet-action-recognition。

读以下材料（论文已转纯文本，用 read 工具读；代码用 read/bash 探索）：
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2606.17590_tivtok.txt  (TivTok, 核心骨架来源)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2406.07550_titok.txt   (TiTok, 1D tokenizer 鼻祖)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/ti_tokenizer/         (TiTok 官方开源代码)

要回答的问题（逐条给出原文/代码证据，标注文件与行号或章节号）：
1. TivTok 的 SIF（Scope-Induced Factorization）在代码/论文里具体怎么实现？TIV tokens 和 TV tokens 的 attention scope 分别是什么？是否用 attention mask 实现？
2. token 数量与维度：N_TIV、N_TV、hidden dim、patch size、位置编码（3D RoPE？）具体数值。
3. encoder/decoder 的具体结构（层数、是否 ViT、解码器如何用 TIV+TV_t 重建第 t 帧，Invariant Broadcasting 怎么做）。
4. 训练配方：损失组成与权重、优化器/LR/warmup/epoch、分辨率、数据（UCF101+K600 怎么用）、batch size。
5. 量化方式（SoftVQ？VQ？连续？）以及 codebook 设置。
6. ti_tokenizer 仓库里哪些代码可复用（1D tokenizer 的 bottleneck attention 实现、训练脚本、config 结构）？给出关键文件路径。
7. TivTok 是否开源？若否，实现 SIF 的最小可行方案是什么。

输出：结构化中文简报，每条结论必须有出处（文件名+章节/行号）。不确定的地方明确标注'论文未说明'。不要臆测。

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