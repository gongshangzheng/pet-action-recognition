# Proposal: behavior-anomaly-detection

> 子 change，总管：`pet-motion-latent-pipeline`。**状态：延后（研究型）**——待 `video-feature-latent` 产出行为簇后启动；用户要求先深入讨论/调研。

## Why

宠物监测的高价值应用是**行为异常识别**（疼痛、生病、发情、异常刻板行为）。管线产出的动作 token（聚类簇 ID 序列或 VQ token）天然支持异常检测范式：**正常行为 = 高频且已被命名的簇；异常 = 低频簇 / 未命名簇 / token 序列的罕见转移**。此前讨论的想法：动作拆 token → 聚类 → 找异常点 → 人工标注簇语义 → 形成异常识别能力。

## What Changes

- **token 序列构建**：两条路线——① HDBSCAN 簇 ID 序列（零训练，主链现成产物）；② VQ 码本 token（video-feature-latent 条件启动的学习版）
- **异常评分机制（需调研）**：候选 = 低频簇统计 / token 转移概率突变（马尔可夫）/ 滑窗 token 直方图 vs 全局分布偏离（JS 散度）/ 孤立森林
- **人工标注闭环**：候选异常簇 → 人看代表帧标注语义（"呕吐""瘸腿"或"正常但罕见"）→ 标注结果反哺簇命名表
- **产出**：异常事件报告（时间段 + 簇 + 语义标签 + 置信度）

## Capabilities

### New Capabilities

- `motion-pipeline` 新增异常检测要求（实施时补 delta；当前为研究备档）

## Impact

- 依赖：video-feature-latent 的行为簇 / token 序列
- 需调研：动物行为学异常检测文献（Keypoint-MoSeq 时序模型、VBS 疼痛行为视频基准、畜牧业跛行检测）
- 数据现实约束：家庭 2-5 只猫，**异常样本极稀少**——大概率走无监督 + 人工确认路线，不做异常样本训练
