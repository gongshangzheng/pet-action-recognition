# 核心论文清单（Core Papers）

> 与数据库标记同步生成（starred=核心收藏，pinned=最重要·置顶展示）。
> 维护方式：修改 `papers/config/core_papers.json` 后运行 `python3 scripts/curate_core_papers.py`。
> 生成日期：2026-08-29

## 筛选标准

1. **奠基性/高影响力**：开创性方法或领域公认基准
2. **项目直接相关性**：与宠物动作识别的训练（mmaction2 registry）、评测、Live 推理直接相关
3. **方向代表性**：动物姿态/行为方向的代表性工作

## ⭐ 置顶核心（Pinned，8 篇）

| # | 论文 | 年份/出处 | 入选理由 | 链接 |
|---|------|----------|---------|------|
| 1 | **VideoMAE** | NeurIPS 2022 | 项目预训练训练路线主力骨干：高掩码率视频自监督，数据效率极高，现有训练 registry 直接使用 | [arXiv:2203.12602](https://arxiv.org/abs/2203.12602) |
| 2 | **Quo Vadis, Action Recognition? (I3D + Kinetics)** | CVPR 2017 | 「人类动作预训练→下游迁移」范式源头，动物迁移路线的方法论基础 | [arXiv:1705.07750](https://arxiv.org/abs/1705.07750) |
| 3 | **SlowFast Networks** | ICCV 2019 | 双路（慢语义+快运动）经典骨干，速度/精度折中长期基准，实时推理参照 | [arXiv:1812.03982](https://arxiv.org/abs/1812.03982) |
| 4 | **Two-Stream ConvNets** | NeurIPS 2014 | 双流（RGB+光流）动作识别奠基作，时序特征演化起点 | [arXiv:1406.2199](https://arxiv.org/abs/1406.2199) |
| 5 | **DeepLabCut** | Nature Neuroscience 2018 | 动物姿态估计事实标准工具，少量标注即可迁移；姿态桥接辅助线的工程基座 | [Nature](https://www.nature.com/articles/s41593-018-0209-y) |
| 6 | **Animal Kingdom** | CVPR 2022 | 850 物种动物行为理解最大基准（动作/姿态/定位三任务），宠物动作识别的对标数据集 | [arXiv:2204.08129](https://arxiv.org/abs/2204.08129) |
| 7 | **SuperAnimal** | Nature Communications 2024 | 跨物种预训练姿态基础模型，SuperAnimal-Quadruped 四足零样本可用，骨架路线首选 | [arXiv:2203.07436](https://arxiv.org/abs/2203.07436) |
| 8 | **MammalNet** | ICCV 2023 | 直接量化 Kinetics 人类预训练迁移到动物行为识别的效果——核心问题二的关键证据 | [arXiv:2306.00576](https://arxiv.org/abs/2306.00576) |

## 🔖 核心收藏（Core，12 篇）

| # | 论文 | 年份/出处 | 入选理由 | 链接 |
|---|------|----------|---------|------|
| 9 | **VideoMAE V2** | CVPR 2023 | 核心问题一主攻：无标注宠物监控视频域继续预训练，数据效率最优单点投入 | [arXiv:2303.16727](https://arxiv.org/abs/2303.16727) |
| 10 | **InternVideo2** | ECCV 2024 | 2024 视频基座代表，60+ 任务 SOTA，强骨干候选 | [arXiv:2403.15377](https://arxiv.org/abs/2403.15377) |
| 11 | **VideoPrism** | ICML 2024 | Google 视频基座编码器，冻结特征评估对小数据场景有吸引力 | [arXiv:2402.13217](https://arxiv.org/abs/2402.13217) |
| 12 | **AIM** | ICLR 2024 | 冻结图像 ViT + 少量 Adapter 达视频 SOTA，参数高效微调是小数据场景关键技术 | [arXiv:2302.03024](https://arxiv.org/abs/2302.03024) |
| 13 | **APT-36K** | NeurIPS 2022 | 首个动物姿态视频追踪基准，人体预训练跨物种迁移的直接证据 | [arXiv:2206.05683](https://arxiv.org/abs/2206.05683) |
| 14 | **AP-10K** | NeurIPS 2021 | 23 科 54 种跨物种姿态基准，含猫狗关键点 | [arXiv:2108.12617](https://arxiv.org/abs/2108.12617) |
| 15 | **OTAM** | CVPR 2020 | few-shot 时序对齐代表，对应稀有动作类别仅几个样本的场景 | [arXiv:1906.11415](https://arxiv.org/abs/1906.11415) |
| 16 | **TRX** | ICCV 2021 | few-shot CrossTransformer 关键一环，适合长短不一的宠物动作片段 | [arXiv:2101.06184](https://arxiv.org/abs/2101.06184) |
| 17 | **FSAR Comprehensive Review** | 2024 | few-shot 动作识别领域全景综述，数据稀缺路线入门地图 | [arXiv:2407.14744](https://arxiv.org/abs/2407.14744) |
| 18 | **Task-Adapter** | 2024 | 图像基础模型适配 few-shot 动作识别，连接两个核心问题 | [arXiv:2408.00249](https://arxiv.org/abs/2408.00249) |
| 19 | **Coarse to Fine-Grained Animal Action Recognition Review** | 2025 | 动物动作识别方向综述地图，优先阅读 | [arXiv:2506.01214](https://arxiv.org/abs/2506.01214) |
| 20 | **Keypoint-MoSeq** | Nature 2024 | 姿态驱动无监督行为分割 SOTA 范式，动物动作自动发现代表 | [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02318-2) |

## 两大核心问题的路线判断（调研结论）

> 依据专题 C 调研（27 篇证据链 + 二轮 API 核验），详见 `openspec/changes/seed-papers-library/`。

### 核心问题二：人类动作识别能力迁移到动物 —— **短期主路线（3–6 个月）**

- 证据链完整：APT-36K、ViTPose++、MammalNet、Animal Kingdom 一致表明 Kinetics/人体预训练迁移显著优于从头训练
- **推荐主路径**：Kinetics 预训练骨干（Video Swin / VideoMAE / InternVideo）+ 自有猫狗切段数据全量微调，与现有 mmaction2 栈完全兼容
- ⚠️ 失效模式：动物特有动作（踩奶、甩尾）在人类动作空间无对应类，微调时保留开放集/未知类检测

### 核心问题一：动物数据稀缺 —— **自监督域继续预训练最优**

- VideoMAE V2 掩码方案在 live 模块无标注监控录像上继续预训练，是数据效率提升最大的单点投入
- few-shot 方法（OTAM/TRX/HyRSM/MoLo）不正面硬刚：每类攒到 20–50 段直接微调即优于 few-shot 技巧；但作为稀有类别的兜底范式值得了解
- 合成数据（SMAL/BARC/AP-CAP 渲染）证据偏姿态、动作保真度弱，仅作辅助增广

### 姿态桥接：低成本高杠杆辅助线

- SuperAnimal-Quadruped 零样本生成关键点 → 伪标注增广 + 骨架轻量动作分类器（对遮挡/背景更鲁棒）
- 工具链：DeepLabCut（微调）→ SLEAP（多动物）→ Keypoint-MoSeq（无监督行为发现）

## 与数据库的一致性

```bash
# 校验清单与标记一致
sqlite3 data/papers.db "SELECT id, title, pinned, starred FROM papers WHERE starred=1 ORDER BY pinned DESC;"
# 重新同步标记
python3 scripts/curate_core_papers.py
```
