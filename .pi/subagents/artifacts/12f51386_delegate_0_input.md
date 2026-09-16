# Task for delegate

你是文献+代码精读员。项目：宠物（猫）动作识别，需要一个'又快又好'的猫本体抠像（背景移除，只留猫）方案，将对全量语料批处理。
只读调研，不要修改任何文件。工作目录 /Users/zhengxinyu/pet-action-recognition。

读以下材料：
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2408.00714_sam2.txt      (SAM 2)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2108.11515_rvm.txt       (Robust Video Matting, RVM)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/txt/2401.03407_birefnet.txt  (BiRefNet, 图像二分分割 SOTA)
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/sam2/
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/rvm/
- /Users/zhengxinyu/pet-action-recognition/third-party/refs/repos/birefnet/

要回答的问题（逐条给出原文/代码证据，标注文件与行号或章节号）：
1. 三者的输入要求与输出形式：SAM2（是否需要 prompt？box 可用吗？输出 mask 还是 alpha？视频传播怎么用）；RVM（是否需要 trimap？输出 alpha？训练域是人物吗）；BiRefNet（输出什么、是否逐帧）。
2. 速度对比：三者论文报告的 FPS/延迟（注明硬件与分辨率），对'批处理数千段视频'哪个更合适。
3. 时序一致性：SAM2 的 memory attention、RVM 的 temporal guidance、BiRefNet 的逐帧问题——对'消除帧间闪烁'哪个最好。
4. 动物/毛发泛化：论文或代码里是否提到对非人类（动物）对象的效果？RVM 是人物训练的吗，对猫是否可靠？SAM2 的零样本对象泛化如何？
5. 代码可运行性：三个仓库的依赖、权重下载方式（含镜像可达性）、许可证、最小调用示例（给出关键函数/文件路径）。
6. 综合推荐：对'猫本体抠像、消除背景运动、批处理数千段视频'，推荐哪个为主、哪个为备选，理由与风险。

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