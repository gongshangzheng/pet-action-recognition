# Tasks: pet-motion-latent-pipeline（总管 change）

> **本 change 是总管**：持有总架构 design（D1–D9）与主 spec；执行任务已拆分为子 change，在此**统一登记、统一排程、统一验收**。
>
> ## 子 change 管理规则（2026-09-16 增补）
> 1. **注册制**：每新建一个子 change，必须同步登记进 §2 路线图表（含编号/依赖/状态），漏登即违规
> 2. **状态机**：`⏸️ 延后/条件` → `⏳ 待前置` → `🔄 进行中` → `✅ 已归档`；状态只在此表更新
> 3. **顺序纪律**：主线子 change 严格按编号顺序；🔬 研究型子 change **不阻塞主线**（可与主线并行或延后），启动需用户指定
> 4. **归档闭环**：子 change 全任务 [x] + 用户验收 → `openspec archive` → 本表状态改"✅ 已归档"并注明归档名
> 5. **执行机**：pet（plf 环境）；每次 GPU 任务前 `nvidia-smi` 查占用；数据产物只写项目路径

## 1. 已完成历史（本 change 直接交付，保留备查）

- [x] 1.1 petlib 接口骨架（plf 环境 / schemas / detection / tracking / keypoints / registry / 契约测试 13 过）
- [x] 1.2 猫居中预处理 Demo + 用户验收（抽样+插值方案定稿；ByteTrack 全帧率版否决；沙发漂移渲染层过滤修复）
- [x] 1.3 关键点提取器对比选型（HRNet/ResNet-101 AP-10K 实测 + crop-first 口径定稿 + **用户裁定：关键点降级为辅助信号**，design D2/D3/D8）

## 2. 子 change 路线图（统一登记表）

| # | 子 change | 内容 | 依赖/触发 | 状态 |
|---|---|---|---|---|
| 2.1 | `multi-object-detect-gate` | 多目标检测（五类）+ 空间关系状态层 | — | ✅ 已归档（2026-09-15） |
| 2.2 | `batch-followcam-extraction` | 全量批处理 34 段 + followcam 产出 | 2.1 | ✅ 1.1-1.6 闭环（34/34 ok，23 分钟；告警段结案=超短红外低在场片段；语料事实：34 段共 14.7 分钟），**待归档** |
| 2.3 | `video-feature-latent` | 零训练选型 + 行为发现 + 探针评测（L1-L2 主链；L4 决策树可选） | 2.2 | ⏳ 待 2.2 归档 |
| 2.4 | `spot-check-cli` | 抽查式推理 CLI + 猫身份登记 | 2.3 | ⏳ 待 2.3 |
| 2.5 | `identity-action-tokenizer` | 🔬 研究型：FLOAT×TiTok 双 token 视频重建 tokenizer（UCF101→猫语料两阶段） | 2.3 阶段二闸门失败，**或用户指定提前** | ⏸️ 已创建待启动 |

### 主线推进清单

- [x] 2.1 multi-object-detect-gate 验收并 archive（2026-09-15；主 spec motion-pipeline 建立）
- [ ] 2.2 batch-followcam-extraction 归档（34/34 完成 + 告警结案，仅差归档动作）
- [ ] 2.3 video-feature-latent 执行（任务 1.1 选型实验起步）→ 验收 → archive
- [ ] 2.4 spot-check-cli 执行 → 验收 → archive
- [x] 2.5 identity-action-tokenizer 已创建登记（⏸️ 条件启动，见上表）

## 3. 收尾（主线子 change 全部归档后）

- [ ] 3.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 3.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 3.3 archive 总管 change（specs 全量同步至主 spec）

## 4. 延后/旁支 change 登记（条件触发，不在主线序内）

| # | 子 change | 触发条件 | 状态 |
|---|---|---|---|
| 4A | `tracker-selection` | 多猫数据出现 | ⏸️ 延后（0/4） |
| 4B | `registry-retrieval` | 用户批准实施（碗/摄像头实例识别 + 猫 Re-ID） | ⏸️ 延后（0/4） |
| 4C | `behavior-anomaly-detection` | video-feature-latent 归档 + 用户发起深入调研 | ⏸️ 延后（0/5） |
