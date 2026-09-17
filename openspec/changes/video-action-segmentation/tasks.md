# Tasks: video-action-segmentation

> 总管：`pet-motion-latent-pipeline` **2.4b**（位于 2.4 `video-feature-latent` 与 2.5 `spot-check-cli` 之间）。
> 领域背景见 [`papers/docs/action-recognition-models.md`](../../../papers/docs/action-recognition-models.md)；概念见 [6 号 §1.8](../../../management/docs/architecture.md)。
> 前置：`identity-action-tokenizer`（提供 `λ`）、`video-feature-latent`（提供段/窗口表征）。GPU 任务前 `nvidia-smi`。

## 1. 准备与调研

- [ ] 1.1 **无监督 TAS 选型精读**：TAEC（2303.05166）/ Temporally-Weighted Hierarchical Clustering（2103.11264）/ CTE（2019）/ ASAL（2023）——记录输入输出契约、是否需要逐帧标注、许可、代码可得性
- [ ] 1.2 **音频范式精读**：无监督分词 + 词表发现（1603.02845）/ 层次 HMM + 时长先验（1806.01665）/ 神经离散化难分词警告（2106.04298）/ pause-based 分段的局限（2203.15479）
- [ ] 1.3 **确定 `T_pause`**：统计 λ 能量低于阈值的连续段时长分布 → 定"停顿 vs 静止型行为"的时长阈值（初值 3–10 s）
- [ ] 1.4 输出契约冻结：段列表字段（`start_sec/end_sec/action_type/confidence/n_primitives`）与秒级换算口径（帧号 ÷ fps，fps=15）

## 2. λ 运动能量预分段（零成本）

- [ ] 2.1 实现能量曲线：`energy(j) = Σ_m |λ_m(j)|`（复用 tokenizer 产出的 λ 序列）
- [ ] 2.2 能量阈值 + 最小时长 → 输出「低能量段」（= 强边界候选）
- [ ] 2.3 按边界把长视频切成「行为块」，产出块清单（起止 + 能量统计）
- [ ] 2.4 **目检**：抽 3–5 段，人工核对"能量边界是否落在知觉上的行为切换点" → 记录命中/漏检/误检率

## 3. 无监督 TAS 细分段 + 类型聚类

- [ ] 3.1 选定实现路径（design D5 的 A/B/C/D），核许可；不可得则按算法自写
- [ ] 3.2 在「行为块内」跑细分段 → 块内边界 + 段表征
- [ ] 3.3 段表征聚类 → 段类型（未命名）；核**类型数**与 `video-feature-latent` 行为簇数的关系
- [ ] 3.4 **跨块合并**：相邻块段类型相同且间隔 < 阈值 → 合并（解决"同一行为被能量边界切开"）
- [ ] 3.5 **静止型行为**接入：`≥T_pause` 的静止段参与聚类，不被当边界丢弃

## 4. 命名与人为裁决

- [ ] 4.1 导出每段代表帧拼图（沿用 `video-feature-latent` 的接触表设施）
- [ ] 4.2 用户人工命名段类型 → 冻结类型表
- [ ] 4.3 与 `video-feature-latent` 的行为簇命名表对齐（同一套词表 vs 两套）

## 5. 评测与验收

- [ ] 5.1 **边界质量**：与人工标注的段边界比对（±1.5 s 容差内的命中率）
- [ ] 5.2 **过分割/欠分割**：每段平均时长、段数分布 vs 人工
- [ ] 5.3 **类型一致性**：多组超参下同一行为的类型稳定性
- [ ] 5.4 **端到端**：选 3 个真实时段跑通「λ → 段列表」，人工核对报告可读性
- [ ] 5.5 结论 + 待定项收敛（design Open Questions）→ 交付给 `spot-check-cli`

> **可选对照（C33 路线）**：若用户愿意做**片段级标注**，可用其作为验收基线（比纯人工目检严格）。
