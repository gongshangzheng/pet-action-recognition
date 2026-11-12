---
title: "裁剪片段训练：与整帧输入对照"
date: "2026-11-07"
run_id: "clipv9-b"
status: "partial"
verdict: "improved"
summary: "按轨迹逐帧框离线渲染 60 帧片段后训练 VideoMAEv2-B：测试集 1,130 条片段 top-1 85.75%、macro-F1 56.23%、balanced 54.62%。按 AGENTS.md 口径，端到端 = 可用率 85.0% × 条件准确率 85.75% ≈ 72.9%，仍未达到 75% 的中期目标。"
source: "results/cat_clip_v9/videomaev2_b"
---

## 背景与目标

此前训练读的是整帧：2880×1620 缩到短边 256 后猫只有十几像素，既解释了检测漏检，也让分类上限受限。本轮把 GroundingDINO 的框真正用于输入——按轨迹生成逐帧框、离线渲染成 60 帧 256×256 片段，训练直接读片段文件。

## 当前问题

把输入从整帧换成按个体轨迹裁剪的片段，条件准确率能提高多少？端到端是否达到 75%？

## 实验设计

同一份 7,350 条片段、同一 seed、同一配方（VideoMAEv2-B、16 帧、间隔 3、256→224、十类、累积 4、20 epoch、每 2 轮验证），只改输入表示：A 臂读整帧（仅跑到 4 轮，因守卫终止），B 臂读离线渲染的裁剪片段。片段框来自单流 OC-SORT 轨迹：取覆盖片段帧数最多的轨迹，插值到逐帧、端点保持、5 帧滑动平均。

## 结果与分析

B 臂测试集 top-1 85.75%、macro-F1 56.23%、balanced 54.62%。逐类看：activity 89.2%、eating 90.8%、prolonged_stationary 87.6%、toileting 77.8%、grooming 76.1%、drinking 68.3%、scratching 56.4%；gnawing 只有 4 个测试样本、recall 0，fall 与 seizure 测试样本为 0，这三类不能作为结论。训练 loss 降到 0.06 而验证 macro-F1 在第 8 轮见顶（52.22%），说明过拟合，验证轮次波动 50–52%。A 臂只有 4 轮（top-1 75.95%、macro-F1 41.36%），与本轮 20 轮不可直接比较，只能作为趋势参考。 异常类现状：scratching 是唯一可评估的异常类（39 个测试样本，recall 56.4%、漏检 43.6%），17 个错误中 11 个流向 activity、其余散在 drinking/prolonged_stationary；反方向也有 12 个 activity 被误报为 scratching，两头都错。gnawing 全语料只有 10 个标注区间（8 个视频），切片后 17 个片段（train 13 / val 0 / test 4），4 个测试样本全部判错（3 个→activity、1 个→eating），属数据量不足，模型侧无解。fall 与 seizure 的测试样本为 0（训练分别只有 1 和 0 个片段），完全无法评估；seizure 唯一的区间被判多宠物排除，待多宠物审阅后可回收。 排除样本量不足的三类（gnawing 4、fall 0、seizure 0）后重新计算：样本 1,126 条，top-1 86.06%、**macro recall 78.03%**、区间级漏检 13.94%。低召回集中在两类：scratching recall 56.4%（39 样本，漏检 43.6%），其错误高度集中——17 个错误里 11 个判成 activity；drinking recall 68.3%（60 样本，漏检 31.7%），错误分散在 activity（9）、prolonged_stationary（5）、eating（3）。两类都有一个共同形态：precision 明显高于 recall（scratching 64.7、drinking 78.8），说明模型倾向于不报这两类，报了大概率是对的。样例核对：被判成 grooming 的 scratching 片段是夜间红外、256×256 下猫几乎贴墙、身体占满画面，抓挠的爪子动作不可辨；被判成 eating 的 drinking 片段是一只长毛猫低头在碗前，画面里看不到碗里是水还是粮——这与语料里已知的 eating/drinking 标注混淆一致。

## 结论与下一步

裁剪输入确实把条件准确率从早期 75.95%（4 轮）抬到 85.75%（20 轮），direction 明确但对照不严格（A 臂轮数不同）。端到端 72.9% 未达标，瓶颈已从“输入表示”转为“可用率与类别不均衡”。下一步：补跑完整 A 臂做同条件对照；处理多宠物区间的标签归属以提升可用率；针对 scratching/drinking 做类别级分析。

## 附录：配置与完整数据

### 环境与配置

- 模型: VideoMAEv2-B（K710 蒸馏预训练），输入 16 帧 × 224
- 数据集: cat_clip_v9：7,350 条渲染片段（256×256、60 帧），train 4,384 / val 1,836 / test 1,130
- 配置: micro-batch 4 + 累积 4、AdamW 5e-5、20 epoch、每 2 轮验证、sqrt 逆频类别权重、num_workers 6
- 运行时间戳: 2026-11-07 07:32→08:27（训练 3,322 秒）+ 08:29（测试 60 秒）
- 执行入口: scripts/remote/run_clipv9_training.sh；models/mmaction2/tools/test.py
- 随机种子: 0

### 局限与边界

① 端到端只有 72.9%，因为可用率仍停在 85%（多宠物 482 区间未纳入、外延失败 143、未映射 34、短区间 33 等）；② 类别极不均衡：activity 占 51%，gnawing/fall/seizure 的 support 为 4/0/0；③ 过拟合明显，loss 0.06 而验证 macro-F1 仅 52%；④ 多宠物区间需要先解决标签归属，本轮未纳入；⑤ 测试集是片段而非区间，端到端数字是估计，需按区间口径复核。；⑥ 异常类中 gnawing（4 个测试样本）、fall（0）、seizure（0）无法评估，scratching 漏检 43.6% 远超目标

### 来源与核查

- run 产物：results/cat_clip_v9/videomaev2_b
- 详细来源见 manifest 各条目的 source 字段；单位、样本量与局限见 manifest 的 metrics 条目。
- 指标与趋势见 metrics.json（series 折线 + tables 指标表）。

