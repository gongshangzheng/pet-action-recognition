# Tasks: pet-motion-latent-pipeline（总管 change）

> **本 change 是总管**：持有总架构 design（D1–D9）与主 spec；执行任务已拆分为子 change，按路线图顺序推进。
> **执行纪律**：严格按路线图顺序；子 change 按自身 tasks 编号顺序执行；子 change 验收通过并 archive 后才启动下一个。
> **执行机**：pet（plf 环境）；每次 GPU 任务前 `nvidia-smi` 查占用。

## 1. 已完成历史（本 change 直接交付，保留备查）

- [x] 1.1 petlib 接口骨架（§1 全 7 项：plf 环境 / schemas / detection / tracking / keypoints / registry / 契约测试 13 过）
- [x] 1.2 猫居中预处理 Demo + 用户验收（抽样+插值方案定稿；ByteTrack 全帧率版否决；沙发漂移渲染层过滤修复）
- [x] 1.3 关键点提取器对比选型（HRNet/ResNet-101 AP-10K 实测 + crop-first 口径定稿 + **用户裁定：关键点降级为辅助信号**，design D2/D3/D8）

## 2. 子 change 路线图（严格顺序）

| # | 子 change | 内容 | 状态 |
|---|---|---|---|
| 2.1 | `multi-object-detect-gate` | 多目标检测（五类）+ 空间关系状态层 | ✅ 已归档（2026-09-15） |
| 2.2 | `batch-followcam-extraction` | 全量批处理 34 段（运动校正降为可选默认禁用，design B2） | ✅ 1.1-1.6 闭环（34/34 ok；告警段=超短红外低在场片段；语料事实：34 段共 14.7 分钟，行为发现主粮在 mammal_v0/cats v1） |
| 2.3 | `video-feature-latent` | 视频特征主表示选型 + 聚类 + 探针评测 | ⏳ 待 2.2 |
| 2.4 | `spot-check-cli` | 抽查式推理 CLI + 猫身份登记 | ⏳ 待 2.3 |

- [x] 2.1 multi-object-detect-gate 验收并 archive（2026-09-15，归档为 2026-09-15-multi-object-detect-gate；主 spec motion-pipeline 建立）
- [ ] 2.2 batch-followcam-extraction 验收并 archive
- [ ] 2.3 video-feature-latent 验收并 archive
- [ ] 2.4 spot-check-cli 验收并 archive

## 3. 收尾（全部子 change 归档后）

- [ ] 3.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 3.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 3.3 archive 总管 change（specs 全量同步至主 spec）

## 4. 延后任务（条件触发，不在路线图内）

### 4A. 跟踪器对比选型 → 已拆为子 change `tracker-selection`（延后，多猫数据出现时启动）

### 4B. 登记-检索架构 → 已拆为子 change `registry-retrieval`（延后，实施待批准）
