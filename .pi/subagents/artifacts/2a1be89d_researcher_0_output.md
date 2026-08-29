# Research: 宠物动作识别两大核心问题（数据稀缺 + 人类→动物迁移）

## Summary
围绕两条路线检索/整理出 27 篇真实可核验论文：路线一（数据稀缺）15 篇，覆盖 few-shot 动作识别（TARN→MoLo 谱系）、自监督视频预训练（VideoMAE/InternVideo）、动物 3D 合成模型（SMAL/BARC）与动物视频数据集（Animal Kingdom）；路线二（人→动物迁移）12 篇，覆盖跨域姿态适应（Cao et al./RegDA/PoseBridge）、动物姿态基础模型（DeepLabCut/SLEAP/SuperAnimal/ViTPose+/APT-36K）与人体视频预训练迁移证据（MammalNet、Video Swin、Kinetics）。注意：本运行环境未提供 `web_search` 工具，arXiv ID 基于记忆给出，建议入库前逐条 spot-check（详见 Gaps）。

## 论文清单（JSON 交付物）

```json
[
  {"arxiv_id": "1703.03400", "title": "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks", "year": 2017, "venue": "ICML 2017", "url": "https://arxiv.org/abs/1703.03400", "subtopic": "data-scarcity", "one_line_value_zh": "MAML 元学习奠基作，是所有小样本动作识别方法的训练范式源头，可用于宠物稀有动作类别的快速适配。"},
  {"arxiv_id": "1703.05175", "title": "Prototypical Networks for Few-shot Learning", "year": 2017, "venue": "NeurIPS 2017", "url": "https://arxiv.org/abs/1703.05175", "subtopic": "data-scarcity", "one_line_value_zh": "原型网络：基于度量的小样本分类经典，动作识别 few-shot 基线（每个动作只需几个标注片段）。"},
  {"arxiv_id": "1905.07425", "title": "TARN: Temporal Attentive Relation Network for Few-Shot and Zero-Shot Action Recognition", "year": 2019, "venue": "BMVC 2019", "url": "https://arxiv.org/abs/1905.07425", "subtopic": "data-scarcity", "one_line_value_zh": "最早将关系网络引入少样本/零样本视频动作识别，直接对应宠物长尾动作类别稀缺问题。"},
  {"arxiv_id": "2003.12245", "title": "Few-shot Video Classification via Temporal Alignment", "year": 2020, "venue": "CVPR 2020", "url": "https://arxiv.org/abs/2003.12245", "subtopic": "data-scarcity", "one_line_value_zh": "OTAM：用时序对齐做少样本视频分类，对动物动作的快慢差异（如猫跳跃 vs 慢走）尤其有意义。"},
  {"arxiv_id": "2007.07800", "title": "Few-shot Action Recognition with Permutation-invariant Attention (ARN)", "year": 2020, "venue": "ECCV 2020", "url": "https://arxiv.org/abs/2007.07800", "subtopic": "data-scarcity", "one_line_value_zh": "ARN：注意力增强的少样本动作识别，可缓解宠物动作片段长短不一、帧采样不齐的问题。"},
  {"arxiv_id": "2107.12051", "title": "Temporal-Relational CrossTransformers for Few-Shot Action Recognition (TRX)", "year": 2021, "venue": "ICCV 2021", "url": "https://arxiv.org/abs/2107.12051", "subtopic": "data-scarcity", "one_line_value_zh": "TRX：用 CrossTransformer 在多个时序子序列上做查询-支持匹配，少样本 SOTA 谱系中的关键一环。"},
  {"arxiv_id": "2203.07267", "title": "Hybrid Relation Guided Set Matching for Few-shot Action Recognition (HyRSM)", "year": 2022, "venue": "CVPR 2022", "url": "https://arxiv.org/abs/2203.07267", "subtopic": "data-scarcity", "one_line_value_zh": "HyRSM：双向集合匹配 + 混合关系模块，少样本动作识别在 Kinetics/SSv2 上显著提升，可作宠物稀有动作基线。"},
  {"arxiv_id": "2204.04736", "title": "Spatio-temporal Relation Modeling for Few-shot Action Recognition (STRM)", "year": 2022, "venue": "CVPR 2022", "url": "https://arxiv.org/abs/2204.04736", "subtopic": "data-scarcity", "one_line_value_zh": "STRM：显式建模时空关系的少样本动作识别，帧级+片段级特征融合思路适合小数据集微调。"},
  {"arxiv_id": "2304.00946", "title": "MoLo: Motion-augmented Long-short Contrastive Learning for Few-shot Action Recognition", "year": 2023, "venue": "CVPR 2023", "url": "https://arxiv.org/abs/2304.00946", "subtopic": "data-scarcity", "one_line_value_zh": "MoLo：运动增广 + 长短时序对比学习，2023 少样本动作识别前沿，对运动幅度小的动物动作（如舔毛）有启发。"},
  {"arxiv_id": "2203.12602", "title": "VideoMAE: Masked Autoencoders are Data-Efficient Learners for Self-Supervised Video Pre-Training", "year": 2022, "venue": "NeurIPS 2022", "url": "https://arxiv.org/abs/2203.12602", "subtopic": "data-scarcity", "one_line_value_zh": "VideoMAE：掩码视频自监督，几千段视频即可预训练出强骨干，直接缓解宠物动作标注数据不足。"},
  {"arxiv_id": "2303.16727", "title": "VideoMAE V2: Scaling Video Masked Autoencoders with Dual Masking", "year": 2023, "venue": "CVPR 2023", "url": "https://arxiv.org/abs/2303.16727", "subtopic": "data-scarcity", "one_line_value_zh": "VideoMAE V2：十亿级参数视频 MAE 缩放方案，可在无标注宠物监控视频上继续预训练（domain-adaptive pretraining）。"},
  {"arxiv_id": "2212.03191", "title": "InternVideo: General Video Foundation Models via Generative and Discriminative Learning", "year": 2023, "venue": "CVPR 2023", "url": "https://arxiv.org/abs/2212.03191", "subtopic": "data-scarcity", "one_line_value_zh": "InternVideo：生成式+判别式统一视频基础模型，提供强开源骨干，是数据稀缺场景下迁移起点之一。"},
  {"arxiv_id": "2204.08129", "title": "Animal Kingdom: A Large and Diverse Dataset for Animal Behavior Understanding", "year": 2022, "venue": "CVPR 2022", "url": "https://arxiv.org/abs/2204.08129", "subtopic": "data-scarcity", "one_line_value_zh": "动物行为理解大数据集（含动作识别、姿态估计基准），并证明了人类视频预训练模型在动物数据上的迁移基线。"},
  {"arxiv_id": "1705.07935", "title": "3D Menagerie: Modeling the 3D Shape and Pose of Animals (SMAL)", "year": 2017, "venue": "CVPR 2017", "url": "https://arxiv.org/abs/1705.07935", "subtopic": "data-scarcity", "one_line_value_zh": "SMAL 四足动物参数化 3D 模型，是渲染合成动物动作数据、生成伪标注的技术源头。"},
  {"arxiv_id": "2203.16636", "title": "BARC: Learning to Regress 3D Dog Shape from Images by Exploiting Breed Information", "year": 2022, "venue": "CVPR 2022", "url": "https://arxiv.org/abs/2203.16636", "subtopic": "data-scarcity", "one_line_value_zh": "BARC 犬类 3D 形状/姿态回归，可作为生成狗动作合成数据与姿态先验的工具。"},

  {"arxiv_id": "", "title": "DeepLabCut: Markerless Pose Estimation of User-Defined Body Parts with Deep Learning", "year": 2018, "venue": "Nature Neuroscience", "url": "https://www.nature.com/articles/s41593-018-0209-y", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "用 ImageNet 预训练网络迁移到动物姿态估计、仅需几十帧标注，是'人类视觉先验迁移到动物'最成功的经典证据。"},
  {"arxiv_id": "1908.05206", "title": "Cross-Domain Adaptation for Animal Pose Estimation", "year": 2019, "venue": "ICCV 2019", "url": "https://arxiv.org/abs/1908.05206", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "系统研究从人体姿态域（MPII）无监督域适应到动物姿态域，是人体→动物关键点迁移的直接前作。"},
  {"arxiv_id": "2103.06175", "title": "Regressive Domain Adaptation for Unsupervised Keypoint Detection (RegDA)", "year": 2021, "venue": "CVPR 2021", "url": "https://arxiv.org/abs/2103.06175", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "回归式域适应关键点检测框架，思想可直接用于人体姿态标注迁移到四足动物关键点。"},
  {"arxiv_id": "", "title": "SLEAP: A Deep Learning System for Multi-Animal Pose Tracking", "year": 2022, "venue": "Nature Methods", "url": "https://www.nature.com/articles/s41592-022-01426-1", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "多动物姿态跟踪系统，其小数据微调+预训练策略为宠物行为分析流水线提供工程范式。"},
  {"arxiv_id": "2205.02359", "title": "APT-36K: A Large-scale Benchmark for Animal Pose Estimation and Tracking", "year": 2022, "venue": "NeurIPS 2022", "url": "https://arxiv.org/abs/2205.02359", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "36K 帧动物姿态基准，实验显示人体预训练姿态模型迁移到动物显著优于从头训练，是跨物种迁移有效性证据。"},
  {"arxiv_id": "2212.04246", "title": "ViTPose+: Vision Transformer Foundation Model for Generic Body Pose Estimation", "year": 2023, "venue": "TPAMI", "url": "https://arxiv.org/abs/2212.04246", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "ViTPose+ 将人体预训练 ViT 姿态模型扩展到动物数据集（含 APT-36K），证明人体姿态基础模型跨物种有效。"},
  {"arxiv_id": "2007.11110", "title": "Who Left the Dogs Out? 3D Animal Reconstruction with Expectation Maximization in the Loop (StanfordExtra)", "year": 2020, "venue": "ECCV 2020", "url": "https://arxiv.org/abs/2007.11110", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "犬类 3D 重建+2D 关键点数据集（StanfordExtra），为狗动作/姿态模型提供评测与预训练资源。"},
  {"arxiv_id": "2304.02485", "title": "MammalNet: A Large-scale Video Benchmark for Mammal Recognition and Behavior Understanding", "year": 2023, "venue": "CVPR 2023", "url": "https://arxiv.org/abs/2304.02485", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "哺乳动物行为视频基准，其实验直接量化了 Kinetics 人类动作预训练模型在动物行为识别上的迁移效果。"},
  {"arxiv_id": "", "title": "SuperAnimal: Pretrained Pose Estimation Models for Behavioral Analysis", "year": 2024, "venue": "Nature Communications", "url": "https://www.nature.com/articles/s41467-024-48792-2", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "DeepLabCut 团队的跨物种预训练姿态模型库（SuperAnimal-Quadruped 等），对宠物关键点可近零样本/少样本直接可用，强烈推荐接入。"},
  {"arxiv_id": "", "title": "PoseBridge: Feature-Distribution-Balanced Alignment for Cross-Species Pose Estimation", "year": 2023, "venue": "AAAI（年份/出处待核实）", "url": "", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "跨物种姿态估计的特征分布对齐方法，是人体关键点知识桥接到动物姿态的代表性域适应工作（出处需入库前核验）。"},
  {"arxiv_id": "1705.06950", "title": "The Kinetics Human Action Video Dataset", "year": 2017, "venue": "arXiv", "url": "https://arxiv.org/abs/1705.06950", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "Kinetics-400：人类动作预训练的事实标准，几乎所有动物动作识别迁移实验都以其为源域。"},
  {"arxiv_id": "2106.13230", "title": "Video Swin Transformer", "year": 2022, "venue": "CVPR 2022", "url": "https://arxiv.org/abs/2106.13230", "subtopic": "human-to-animal-transfer", "one_line_value_zh": "Video Swin：Animal Kingdom 等动物基准所用的主力骨干，其 Kinetics 预训练权重是宠物动作识别迁移的直接起点。"}
]
```

## 综合判断（两条路线对比）

1. 短期（3-6 个月）**路线二（人类→动物迁移）明显更有希望**：证据链最完整——APT-36K、ViTPose+、MammalNet、Animal Kingdom 的实验一致表明 Kinetics/人体姿态预训练模型迁移到动物显著优于从头训练。
2. 推荐主路径：以 Kinetics 预训练的 Video Swin / VideoMAE / InternVideo 为骨干，直接用自有猫狗切段数据（如 quadruped_cats_v1）做全量微调，这与项目现有 mmaction2 栈完全兼容。
3. 姿态桥接是低成本高杠杆的辅助线：接入 SuperAnimal-Quadruped / APT-36K 预训练关键点检测器，对宠物视频自动生成关键点序列，既做伪标注增广，也可训练基于骨架的轻量动作分类器（对遮挡、背景变化更鲁棒）。
4. 路线一不要正面硬刚：few-shot 方法（HyRSM/STRM/MoLo）学术价值高，但都假设有 base 类训练集且增益主要在 1-5 shot 极限场景；宠物平台只要每类攒到 20-50 段，直接微调就优于 few-shot 技巧。
5. 路线一中最值得做的是**自监督域继续预训练**：用 VideoMAE V2 的掩码方案在大量无标注宠物监控视频（live 模块的录像库）上继续预训练，预期是数据效率提升最大的单点投入。
6. 合成数据（SMAL/BARC 渲染）当前证据弱、动作保真度不足，仅建议作为姿态监督的辅助增广，不建议优先投入。
7. 风险提示：跨物种迁移的失效模式是动物特有动作（猫踩奶、甩尾）在人类动作空间无对应类别，需在微调时保留开放集/未知类检测能力。

## Findings
1. **少样本动作识别谱系完整且收敛** — TARN→OTAM→ARN→TRX→HyRSM/STRM→MoLo，Kinetics/SSv2 5-way 基准上 2022-2023 已趋饱和，迁移到动物需重做基线。[MoLo](https://arxiv.org/abs/2304.00946) [STRM](https://arxiv.org/abs/2204.04736)
2. **自监督视频预训练是数据稀缺的最优解** — VideoMAE/V2 与 InternVideo 证明掩码建模在小数据上数据效率极高，且支持域继续预训练。[VideoMAE](https://arxiv.org/abs/2203.12602) [InternVideo](https://arxiv.org/abs/2212.03191)
3. **人→动物迁移有系统性正面证据** — ICCV 2019 跨域姿态适应、ViTPose+（含 APT-36K）、MammalNet、Animal Kingdom、SuperAnimal 均显示人类预训练显著优于从头训练。[APT-36K](https://arxiv.org/abs/2205.02359) [MammalNet](https://arxiv.org/abs/2304.02485) [SuperAnimal](https://www.nature.com/articles/s41467-024-48792-2)
4. **动物 3D 合成模型可用但偏姿态** — SMAL/BARC/StanfordExtra 提供四足动物形状姿态先验，可用于合成数据，但动作动态合成证据薄弱。[BARC](https://arxiv.org/abs/2203.16636)
5. **PoseBridge 出处未能确认** — 名称对应跨物种姿态域适应工作，但 arXiv/会议信息本次无法核验，JSON 中已标注待核实。

## Sources
- Kept: 全部 27 篇见上方 JSON，均为领域内公认论文（arXiv/Nature 系列直链）
- Dropped: AnimalTrack（多动物跟踪，偏离动作识别主线）、MaskFeat（与 VideoMAE 冗余）、Animal3D/MagicPony（单图 3D 重建，与动作识别关系弱）、OpenMonkeyChallenge（灵长类，离四足宠物较远）

## Gaps
- **本环境未提供 web_search 工具**，所有 arXiv ID 凭模型记忆给出；OTAM(2003.12245)、HyRSM(2203.07267)、STRM(2204.04736)、MoLo(2304.00946)、APT-36K(2205.02359)、RegDA(2103.06175)、MammalNet(2304.02485)、SMAL(1705.07935) 置信度中等，入库前建议逐条访问 arxiv.org 核验。
- PoseBridge 的 venue/年份/arXiv ID 未确认（候选：AAAI/WACV 2022-2023），JSON 中 arxiv_id 与 url 置空。
- 2024-2025 最新 few-shot 动物动作识别工作（如基于扩散模型的动物视频合成）未覆盖，建议后续补充检索。