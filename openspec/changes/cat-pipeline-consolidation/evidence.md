# 证据

### 2026-11-08：四个 change 归档

- 归档：`clip-box-crop-input`、`cat-clip-ten-class-training`、`multi-pet-track-cropping`、`multi-pet-sort-tracking`，均移入 `openspec/changes/archive/2026-11-08-*`。
- **标记口径**：三份含未勾选条目的 change 把剩余条目统一标为「【移交】…（后续在 cat-pipeline-consolidation 执行）」。注意其中有一部分（如逐帧框、离线渲染、十类训练）**实际已经执行**，只是因为 tasks 多次重写没有同步勾选；它们的真实结果记录在本 change 的「已完成」小节与对应报告中，不依赖旧 change 的勾选状态。
- 两份带 delta spec 的 change（`clip-box-crop-input`、`multi-pet-sort-tracking`）在归档时已把 delta 合入主 spec。
- 后续唯一推进入口是本 change；旧 change 原文保留供追溯。
