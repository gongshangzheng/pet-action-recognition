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
