# Tasks: video-feature-latent

> 总管：`pet-motion-latent-pipeline`。前置：`batch-followcam-extraction` 完成。严格按编号顺序执行。

- [ ] 1.1 主表示选型实验：VideoMAEv2 vs DINOv2 在两段验收跟随视频 + 抽 3 段白天段上各出窗口特征（16 帧窗口 stride 8）→ UMAP 可视化 + 时序连续性（相邻窗口余弦距离）→ 人工看簇代表帧可命名性；判定：可命名簇比例为主，打平取 VideoMAEv2
- [ ] 1.2 胜出编码器接入 petlib（`petlib/features/` 抽象 + 契约测试复用）
- [ ] 1.3 全量窗口特征提取 + UMAP(30) → HDBSCAN → 行为簇
- [ ] 1.4 可命名率报告：各簇代表帧（叠加关键点辅助参考）+ 人工抽 30 簇判定（**用户验收节点**）
- [ ] 1.5 `scripts/discover_behaviors.py`：聚类 → 代表帧 → 人工命名表；NMI/ARI 报告（聚类 vs 5 类人工标注）
- [ ] 1.6 `scripts/train_linear_probe.py`：线性探针 top1——主对照 = 同一编码器原始整帧特征；参考 = VideoMAEv2 全量微调基线
- [ ] 1.7 （条件）自训 VQ 版：可命名率 <60% 或探针不达标时启动（总管 D3：输入 48×768 视频特征，VQ K=512，码本利用率 ≥50%）
- [ ] 1.8 （可选）消融：HQSAM mask 清洗 crop；摄像机策略对比（follow_adaptive vs follow_locked vs fixed）
- [ ] 1.9 （可选）决策树蒸馏：簇命名后用 (特征→簇名) 训浅决策树（可读运动学特征优先），验证规则可读性 + spot-check 免聚类推理；备选无监督树（预测聚类树/层次聚类多粒度）见 design L4
- [ ] 1.10 （路线 W，第二阶段）调研 Wav2vec2/HuBERT/LatentSync 判别式目标配方（W1 迭代伪标签 masked prediction / W2 InfoNCE 时序对比；mask 比例/epoch/数据高效口径），产出域内预训练方案——**目标函数 = 判别式优先（区分动作为第一性）**
- [ ] 1.11 （路线 W，条件）在 ~3k 段无标注语料上继续预训练 VideoMAE（4090，先查占用）→ 重提行为素 → 与第一阶段三候选同台对比可命名率
