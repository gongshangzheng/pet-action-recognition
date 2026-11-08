# Tasks: behavior-anomaly-detection

> 总管 §2 路线图之外的研究型 change：启动时机 = `video-feature-latent` 归档后 + 用户发起深入讨论。**启动前本 change 不排期。**

- [ ] 1.1 文献调研：动物行为异常检测（Keypoint-MoSeq / VBS 疼痛基准 / 畜牧跛行检测）+ 时序离散 token 异常机制 → 调研纪要沉淀本 design
- [ ] 1.2 token 序列构建：行为簇 ID 序列（逐窗口）+ 簇转移矩阵，落盘 schema 定义
- [ ] 1.3 异常评分原型：AN2 至少两种机制实现，在 34 段白天数据上出候选异常列表
- [ ] 1.4 人工标注闭环试用：用户看候选簇代表帧标注语义 → 异常/正常罕见 二分
- [ ] 1.5 评估报告：候选异常的精度人工判定 + 机制对比 → 决定是否进入 spot-check-cli 的报告格式
