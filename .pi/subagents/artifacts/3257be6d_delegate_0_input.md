# Task for delegate

你是文献+代码精读员。项目：宠物（猫）动作识别，正在设计身份-动作解耦视频 tokenizer，其中动作通道要用 FLOAT/LIA 的正交运动基。
只读调研，不要修改任何文件。工作目录 /Users/zhengxinyu/pet-action-recognition。

读以下材料：
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2412.01064_float.txt  (FLOAT, ICCV 2025)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2203.09043_lia.txt     (LIA, ICLR 2022, FLOAT 的正交基来源)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/float/               (FLOAT 官方开源代码)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/lia/                 (LIA 官方开源代码)

要回答的问题（逐条给出原文/代码证据，标注文件与行号或章节号）：
1. 正交运动基到底怎么实现的？LIA 说 'implement D_m as a learnable matrix and apply Gram-Schmidt during each forward pass'——请找到代码里的具体位置（文件+行号）并给出实现细节（是 torch.nn.utils.parametrizations.orthogonal？手写 Gram-Schmidt？每次 forward 调用？）。
2. 潜空间分解 w_S = w_{S→r}(身份) + w_{r→S}(运动) 在代码里怎么落地？两个分量分别由什么产生（编码器输出还是线性层）？
3. 运动系数 λ 如何提取（闭式内积？）；d 和 M 的具体数值；代码里的对应参数名。
4. FLOAT 相对 LIA 改了什么（除面部组件损失外）？FLOAT 的 motion latent auto-encoder 训练目标完整列表与权重。
5. LIA/FLOAT 是否依赖光流（flow field）？如果我们要把正交运动基移植到'视频 tokenizer 的动作 latent'（不用光流、不用 warp），哪些部分可直接借用、哪些必须改？
6. 两个仓库的依赖与可运行性（是否可 pip 安装、权重是否可得、许可证）。

输出：结构化中文简报，每条结论必须有出处（文件名+行号/章节）。不确定标注'论文/代码未说明'。不要臆测。

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