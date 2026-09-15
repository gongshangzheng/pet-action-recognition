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
| 2.1 | `multi-object-detect-gate` | 多目标检测（五类）+ 空间关系状态层 | 🔄 进行中（待用户验收 1.4） |
| 2.2 | `batch-followcam-extraction` | 全量批处理 34 段（含逐帧运动校正，design B2） | ⏳ 待 2.1 验收 |
| 2.3 | `video-feature-latent` | 视频特征主表示选型 + 聚类 + 探针评测 | ⏳ 待 2.2 |
| 2.4 | `spot-check-cli` | 抽查式推理 CLI + 猫身份登记 | ⏳ 待 2.3 |

- [ ] 2.1 multi-object-detect-gate 验收并 archive
- [ ] 2.2 batch-followcam-extraction 验收并 archive
- [ ] 2.3 video-feature-latent 验收并 archive
- [ ] 2.4 spot-check-cli 验收并 archive

## 3. 收尾（全部子 change 归档后）

- [ ] 3.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 3.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 3.3 archive 总管 change（specs 全量同步至主 spec）

## 4. 延后任务（条件触发，不在路线图内）

### 4A. 跟踪器对比选型（多猫数据出现时启用）

> BoxMOT 四候选（ByteTrack/OC-SORT/BoT-SORT/DeepSORT）已装 plf 备用；原理见 design D1c。

- [ ] 4.1 GT 制作：抽 3–5 段白天视频（含多猫），人工核对 track_id
- [ ] 4.2 固定检测源缓存 + 运行四候选
- [ ] 4.3 指标（IDF1/IDSW/碎片/平滑度）+ 选型报告（决定 CLI 默认跟踪器）
- [ ] 4.4 检测器侧误报抑制消融记录：阈值扫描已预跑——0.3→0.5 均无法抑制沙发超宽框；沙发漂移由渲染层尺寸离群过滤兜底，multi-object-detect-gate 验收后升级为沙发框语义校验

### 4B. 登记-检索架构（design D9，用户确认方向，实施待批准）

- [ ] 4.5 （待批准）统一登记-检索库：登记照 → DINOv2 embedding → FAISS；猫与物品共用一套
- [ ] 4.6 （待批准）静态物体候选生成：SAM 一次性分割（固定机位缓存 + 定期重分割）+ 帧差变更触发；解决文本检测不到碗/摄像头的问题
- [ ] 4.7 （待批准）物品实例识别闭环：SAM mask 候选 → DINOv2 检索判定；OWLv2 图像引导作对照；GroundingDINO LoRA 室内微调仅作最后手段备档
- [ ] 4.8 （待批准）猫 Re-ID 联调：与 spot-check-cli 的 register_cats.py 合并设计
