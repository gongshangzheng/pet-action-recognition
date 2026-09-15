# Proposal: video-feature-latent

> 子 change，总管：`pet-motion-latent-pipeline`。前置：`batch-followcam-extraction` 完成（跟随视频资产就绪）。

## Why

**终局需求**：管线的最终产品是"抽查式动作报告"（`spot-check-cli`：指定时段 → 输出"14:03–14:12 睡觉/进食"）与行为异常识别——两者都依赖一层**动作语义**。

**当前缺口**：`batch-followcam-extraction` 完成后，我们只拥有"猫在哪"（逐帧框、跟随视频），"猫在干嘛"这一层完全空白。而人工标注的 5 类活动表不可靠（activity 伞类占一半，见总管 Context）——这正是本 change 要用无监督发现解决的原始痛点：**让数据自己告诉我们猫的行为有哪几类，而不是人先拍脑袋定类别**。

**方案与代价**：跟随视角视频 → 预训练视频编码器窗口特征（行为素）→ UMAP+HDBSCAN 聚类 → 行为簇 → 人工看代表帧命名 → 动作时间轴。选零训练路线的原因：① 不训新模型，几小时 GPU 即可验证可行性；② 无监督能发现"标注表里没有的未知行为"；③ 探针评测给出量化下限。若可命名率 <60% 才触发自训 VQ 版（可选增强）。

**时机（0B 裁定转折，2026-09-14）**：主表示原定为关键点序列（48×34），关卡 0B 实测 AP-10K 关键点在家猫特写域 conf 仅 0.35–0.45、四肢点 <0.25，用户判定不可用 → 关键点降级辅助，主表示切换为预训练视频编码器特征（design D2/D8 记录全程）。

## What Changes

- 主表示选型实验：VideoMAEv2 vs DINOv2 窗口特征（16 帧窗口 stride 8）同台对比
- 胜出编码器接入 petlib（`petlib/features/` 抽象 + 契约测试）
- 全量窗口特征 → UMAP + HDBSCAN 行为簇 → 可命名率报告（用户验收节点）
- 线性探针评测：跟随视角特征 vs 原始整帧特征（主对照）
- （条件）自监督 VQ 学习版：仅当零训练基线不达标时启动

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 隐空间表征以预训练编码器零训练特征为主链；关键点降级辅助

## Impact

- `petlib/features/`（新增抽象 + 实现）
- `scripts/discover_behaviors.py`、`scripts/train_linear_probe.py`
- 特征资产（gitignore）：窗口特征 NPZ、聚类结果
