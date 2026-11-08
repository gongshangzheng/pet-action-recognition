## Why

猫行为数据到训练的链路分散在五个 change 里：已归档的 `cat-data-preprocessing`，活跃的 `clip-box-crop-input`、`cat-clip-ten-class-training`、`multi-pet-track-cropping`、`multi-pet-sort-tracking`。已经完成的部分（数据清洗、逐帧框、离线渲染、十类训练与冻结测试）分散在各自的 tasks 与 evidence 中，尚未决定的部分（采样间隔对齐、activity 边界、分辨率、多宠物标签归属、稀有类补数据）也分散在四个 Open Questions 里，无法一眼看清整体状态和下一步。

## What Changes

- 把上述五个 change 的**已完成结果**汇总到本 change 的「已完成」小节，逐条标注证据来源（报告、evidence、提交）。
- 把**仍需实验确定**的问题集中列出，每条给出假设、对照方式、判据与预估成本。
- 原先各 change 保留原文作为过程记录，在本 change 中注明它们的边界；不再往旧 change 里追加新任务。

## Capabilities

无新增或修改能力：这是把既有变更与待定项收拢的工作流整理，行为契约不变（`skip_specs: true`）。

## Impact

- 只影响 OpenSpec 变更的组织方式与后续排期，不改代码、不改数据集。
- 后续实验从本 change 的「待实验」清单开始推进；旧 change 完成归档后仍可追溯。
