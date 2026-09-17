# Tasks: pet-motion-latent-pipeline（总管 change）

> **本 change 是总管**：持有总架构 design（D1–D9）与主 spec；执行任务已拆分为子 change，在此**统一登记、统一排程、统一验收**。
>
> ## 子 change 管理规则（2026-09-16 增补）
> 1. **注册制**：每新建一个子 change，必须同步登记进 §2 路线图表（含编号/依赖/状态），漏登即违规
> 2. **状态机**：`⏸️ 延后/条件` → `⏳ 待前置` → `🔄 进行中` → `✅ 已归档`；状态只在此表更新
> 3. **顺序纪律**：主线子 change 严格按编号顺序；🔬 研究型子 change 仍按编号上线（2026-09-16 裁定：encoder 优先于下游消费方；研究型子 change 升主线的判定权在用户）
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
| 2.3 | `identity-action-tokenizer` | 🔬 升主线（encoder 优先）：**FLOAT 式参考输入 + 正交运动基**（身份由 register tokens 从参考融合、动作由 3D tubelet + QR 正交基得到；UCF101→猫语料两阶段） | 2.2 | ⏳ 待 2.2 归档 |
| 2.3b | `pet-background-removal` | 猫本体抠像（背景移除，只留猫）——消除背景运动对动作通道的污染 | 可并行 2.3 阶段 A；**2.3 阶段 B 前必须完成** | 📋 已创建待启动 |
| 2.4 | `video-feature-latent` | 消费 2.3 编码器做行为发现 + 探针评测（现成 backbone 降为回退） | 2.3 | ⏳ 待 2.3 |
| **2.4b** | **`video-action-segmentation`** | **行为素 → 动作段**：λ 能量预分段 + 无监督 TAS 细分段 + 类型聚类 + 人工命名（产出段列表供出口）| 2.4（且消费 2.3 的 λ）| 📋 已创建待启动（2026-09-17 立项） |
| 2.5 | `spot-check-cli` | 抽查 CLI + 实时监控模式 + 猫身份登记 | **2.4b** | ⏳ 待 2.4b |

### 主线推进清单

- [x] 2.1 multi-object-detect-gate 验收并 archive（2026-09-15；主 spec motion-pipeline 建立）
- [ ] 2.2 batch-followcam-extraction 归档（34/34 完成 + 告警结案，仅差归档动作）
- [ ] 2.3 identity-action-tokenizer 执行（任务 1.1 配方精读→ 1.2 pet_tokenizer 环境→ 1.3 UCF101 manifest→ 2.x tokenizer 实现→ 3.x 阶段 A→ 4.x 阶段 B）→ 验收 → archive
- [ ] 2.3b pet-background-removal 执行（选型实测 → 抠像管线 → 全量批处理）→ 验收 → archive（**2.3 阶段 B 前置**）
- [ ] 2.4 video-feature-latent 执行（直接消费 2.3 编码器，零训练选型作回退）→ 验收 → archive
- [ ] 2.5 spot-check-cli 执行 → 验收 → archive

## 3. 收尾（主线子 change 全部归档后）

- [ ] 3.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 3.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 3.3 archive 总管 change（specs 全量同步至主 spec）

## 4. 延后/旁支 change 登记（条件触发，不在主线序内）

| # | 子 change | 触发条件 | 状态 |
|---|---|---|---|
| 4A | `tracker-selection` | **重启（2026-09-17）**：触发由「等出现多猫」改为「**主动核实**」——「单猫」是未核实假设（批处理报告自己打了「多猫？」问号未答）；且单猫也有收益（lost 语义/误报抑制）。新增前置闸门 tasks 0.x 多猫核实 | ⏳ **待核实**（0/6，含前置闸门）|
| 4B | `registry-retrieval` | 用户批准实施（碗/摄像头实例识别 + 猫 Re-ID） | ⏸️ 延后（0/4） |
| 4D | `background-object-memory`（暂名，待立项）| L1 背景对象层：SAM 关键帧分割 + 场景常驻物体清单 + 纠正/补全 GDINO | 待用户审定 C23（触发信号）后立项 | 🔍 待登记（机制成稿在 `registry-retrieval` R1/R2/R2b）|
| 4C | `behavior-anomaly-detection` | video-feature-latent 归档 + 用户发起深入调研 | ⏸️ 延后（0/5） |
