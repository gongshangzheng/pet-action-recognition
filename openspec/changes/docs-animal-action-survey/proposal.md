# Proposal: docs-animal-action-survey

## Why

seed-papers-library 已完成两轮调研并入库 212 篇论文，但现有 `papers/docs/research-landscape.md` 是**概览版**（六条路线各一段 + 结论清单）。团队需要一份**正式的论文综述文档**：系统梳理动物动作识别 + 宠物动作方向的论文脉络、最新方法（2024–2026）、以及各方法对本项目的适用性判断——作为组内阅读地图和方案选型依据。概览版保留作索引，综述版做深度。

## What Changes

- **新增综述文档** `papers/docs/animal-action-survey.md`（中文，正式综述体例）：
  - 动物动作识别领域综述：从行为学工具（JAABA/MoSeq 时代）到深度学习时代（视频像素路线 vs 姿态驱动路线）的完整脉络
  - 宠物/家养动物子领域现状：DECADE → Animal Kingdom/MammalNet → 2024–2026 最新（AnimalMotionCLIP、DiffPose-Animal、Promptable Animal Pose Tracking、BehaviorVLM 等），标注「pet action recognition 检索为空」的空白机会
  - 最新方法专节：2024–2026 逐篇精讲（动机/方法/结果/对本项目启示）
  - 两大核心问题（数据稀缺、人→动物迁移）的证据链与方法对比表
  - 阅读顺序建议（必读 10 篇 → 方向深入）
- **概览版** `research-landscape.md` 头部加交叉链接指向综述版
- **数据来源**：论文库 DB（212 篇）、`research-verified.json`（核验状态）、两轮调研 artifacts；所有引用 arXiv ID 均为已核验条目

## Capabilities

（纯文档变更，无系统行为变化 → `skip_specs: true`）

### New Capabilities

（无）

### Modified Capabilities

（无）

## Impact

- **文档**：`papers/docs/animal-action-survey.md`（新增，预计 400–600 行）、`papers/docs/research-landscape.md`（加交叉链接）
- **无代码/数据/配置改动**，不涉训练与远端

## 假设记录

- 「动物识别」按上下文理解为**动物动作识别**（animal action recognition），不含物种图像分类
- 综述深度：每个方法段落含「一句话结论 + 对本项目的适用性判断」，不逐篇全文精读（以摘要+调研结论为据）
