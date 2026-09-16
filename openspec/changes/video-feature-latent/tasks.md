# Tasks: video-feature-latent

> 总管：`pet-motion-latent-pipeline`。前置：`batch-followcam-extraction` 完成。严格按编号顺序执行。

- [ ] 1.1 主表示选型实验（design L1 v2 四候选）：**A. VideoMAE v1 宠物微调版 / B. DINOv2+帧间差分 / C. MammalNet（权重可得性待探）/ D. V-JEPA 2 fpc16（新主力，需 pet_vjepa 环境 transformers≥4.55）**——在两段验收跟随视频 + 抽 3 段白天段上各出窗口特征 → UMAP 可视化 + 时序连续性 + 人工可命名性；判定：可命名簇比例为主
- [ ] 1.2 胜出编码器接入 petlib（`petlib/features/` 抽象 + 契约测试复用）
- [ ] 1.3 全量窗口特征提取 + UMAP(30) → HDBSCAN → 行为簇
- [ ] 1.4 可命名率报告：各簇代表帧（叠加关键点辅助参考）+ 人工抽 30 簇判定（**用户验收节点**）
- [ ] 1.5 `scripts/discover_behaviors.py`：聚类 → 代表帧 → 人工命名表；NMI/ARI 报告（聚类 vs 5 类人工标注）
- [ ] 1.6 `scripts/train_linear_probe.py`：线性探针 top1——主对照 = 同一编码器原始整帧特征；参考 = VideoMAEv2 全量微调基线
- [ ] 1.7 （条件）自训 VQ 版：可命名率 <60% 或探针不达标时启动。**架构 = FLOAT 双分解 + CatHuBERT 合流（design L3）**：E_mot（动作，VQ K=512，迭代伪标签 CE 精炼）+ E_id（身份，InfoNCE track 级监督，子空间独立）+ GRL 辅助；码本利用率 ≥50%
- [ ] 1.8 （可选）消融：HQSAM mask 清洗 crop；摄像机策略对比（follow_adaptive vs follow_locked vs fixed）
- [ ] 1.9 （可选）决策树蒸馏：簇命名后用 (特征→簇名) 训浅决策树（可读运动学特征优先），验证规则可读性 + spot-check 免聚类推理；备选无监督树（预测聚类树/层次聚类多粒度）见 design L4
- [x] 1.10 路线 W 方案设计定稿：**CatHuBERT 式行为素迭代预训练**（design L6）——首选 HuBERT 式迭代伪标签 CE（无负样本陷阱），Wav2vec2 InfoNCE 留作对照；骨干冻结 + <10M 小 Transformer（符合参数高效目标）
- [ ] 1.13 （L7 跨域迁移实验）V-JEPA 2 fpc16 在 pet_action_mammal_v0 七类上微调（pet_vjepa 环境，bf16+梯度检查点，~2-4h）→ 对比 VideoMAE v1 基线 top1 → 迁移性成立则确立 CatHuBERT 骨干首选；其冻结特征加入 1.1 选型对比
- [ ] 1.11 （路线 W 实施）第 0 步全语料窗口特征提取（~1h）→ k-means K=256 伪行为素 → 小 Transformer 遮窗预测（2 轮迭代，4090 半天内）→ **四闸门验收**（线性可分性/可命名率/码本健康度/**身份泄漏审计**，design L6+L6b）→ 与 L1 三候选同台对比
- [ ] 1.12 （L6b）身份纠缠审计：DINOv2 伪身份 × 伪行为素 NMI 报告；超阈值则逐档启用归一化/GRL/平衡采样
- [ ] 1.11 （路线 W，条件）在 ~3k 段无标注语料上继续预训练 VideoMAE（4090，先查占用）→ 重提行为素 → 与第一阶段三候选同台对比可命名率
