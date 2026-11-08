# 证据

### 2026-11-08：四个 change 归档

- 归档：`clip-box-crop-input`、`cat-clip-ten-class-training`、`multi-pet-track-cropping`、`multi-pet-sort-tracking`，均移入 `openspec/changes/archive/2026-11-08-*`。
- **标记口径**：三份含未勾选条目的 change 把剩余条目统一标为「【移交】…（后续在 cat-pipeline-consolidation 执行）」。注意其中有一部分（如逐帧框、离线渲染、十类训练）**实际已经执行**，只是因为 tasks 多次重写没有同步勾选；它们的真实结果记录在本 change 的「已完成」小节与对应报告中，不依赖旧 change 的勾选状态。
- 两份带 delta spec 的 change（`clip-box-crop-input`、`multi-pet-sort-tracking`）在归档时已把 delta 合入主 spec。
- 后续唯一推进入口是本 change；旧 change 原文保留供追溯。

### 2026-11-08：旧内容的最终整理

- **提取的核心要义**：写入本 change 的 design 第 5 节，分检测、跟踪、片段与裁剪、数据集数字、训练与评测、已知标注问题六组，每条带出处（归档 change 或报告）。
- **删除的边缘内容**：记在 design 第 6 节，包括三臂实验中 A/C 的评测（只训 B 已定）、20 段小批审阅页与灰度回退调试、`slice_smoke`/`slices_v1`–`v7` 中间版本（数字已被 v8 取代）、SAM 框细化与 MobileSAM 选型（探针结论为不接入）。
- **tasks 精简**：删除「稀有类补数据评估」一条（属预算决策，不构成实验）；其余 7 条待实验保持顺序与判据不变，总数 15 → 14。
- **`gdino-crop-videomaev2-evaluation` 归档**：其“只训 B 臂”的结论与其数据已并入本 change，原文保留在 archive。

### 2026-11-08：任务细分（用户要求）

- 待实验由 7 条拆为 20 条，按“先量化再决定 → 实现 → 对照”分组，每条一个可判定结果。
- 旧号到新号：2.1 → 2.1 + 2.2 + 2.3；2.2 → 3.1 + 3.2 + 3.3；2.3 → 4.1–4.4；2.4 → 5.1 + 5.2；2.5 → 5.3 + 5.4；2.6 → 6.1 + 6.2；2.7 → 7.1–7.4。已完成的小节 1 未改动。
- 并行标注：2.1↔2.2、3.1↔2.1、5.3↔5.1、6.1↔4.3 与 5.2、7.1↔6.1。
- 段落编号从“2. 待实验”变为 2–7 六节；后续引用旧编号的地方以本条映射为准。

### 2026-11-08：已完成工作拆成实现细节

- 原「已完成（汇总）」7 条展开为 8 组 26 条，每条写清具体实现（脚本、参数、数值）与证据出处；全部标为已完成。
- 展开依据：已归档的 `cat-data-preprocessing`、`clip-box-crop-input`、`cat-clip-ten-class-training`、`multi-pet-sort-tracking` 的 evidence，以及两份实验报告。
- 编号变化：原 1.1–1.7 改为 1.1.1–1.8.3；待实验小节编号 2–7 未变。
