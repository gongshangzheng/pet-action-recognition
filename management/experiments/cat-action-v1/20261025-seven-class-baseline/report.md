---
title: "七类区间基线：两模型对比与参考批次"
date: "2026-10-25"
run_id: "cat-action-v1"
status: "complete"
verdict: "improved"
summary: "七类闭集基线分三步落地：先用 24 条区间跑通 TSN 全链路（val top-1 16.67%，只证明链路可跑）；再在 2,710 个区间上训 TSN 与 TSM 两个基线，测试集 top-1 79.19%（TSM）与 72.85%（TSN），TSM 胜出；最后补训四个视频骨干（VideoMAEv2-B、X3D-S、SlowFast-R50、UniFormerV2-B），按冻结规则选出 VideoMAEv2-B（测试 top-1 81.90%）。这些都是区间级结果，不是连续视频的事件级准确率与漏检率。"
source: "docs/cat_action_training_v1.md"
---

## 背景与目标

闭集行为识别的第一条完整基线建立在七类标签上：`activity`、`eating`、`drinking`、`prolonged_stationary`、`grooming`、`toileting`、`abnormal`（把 scratching、gnawing、fall、seizure 合为一类）。这一轮要回答三个层次的问题：整条链路能不能跑通；用哪个模型当基线；换更强的视频骨干能不能把准确率抬上去。

评测单位是**标注区间**：一个区间算一个样本，预测对不对按区间判。这个单位与「连续视频里动作起止抓得准不准」是两件事，正文里的所有数字都只在前一种意义上成立。术语「macro-F1」是七个类别 F1 的算术平均，它对小类比 top-1 敏感得多。

在七类之前还有一代五类实验（79 段素材按 2 秒步长切 4 秒片段）。它把训练、评测、推理链路跑通了，但素材只覆盖单机位单日、测试集只有 101 条，数字不能与本文的区间级结果并列。本文把它放在附录作历史对照。

## 当前问题

做基线之前，必须先分开三件事，因为它们需要的证据不同：

1. **链路是否可跑**（正确性）：数据读取、解码、训练、验证、checkpoint、独立测试、结果记录是否都能产出。这一层只需要证明流程无错，不需要分数有解释力。
2. **哪个模型做基线**（对照）：同数据同划分同配方下，两个候选模型的差距有多大。
3. **换骨干是否有收益**（对照）：四个视频骨干在同样的数据与划分上，测试表现能否超过基线。

三个问题不能混在一起回答。用 24 条区间跑出的准确率回答不了「哪个模型更好」；用验证集排名回答不了「测试集上谁更强」；用区间级答案也回答不了事件级漏检。

## 实验设计

**第一步：链路验证（2026-10-23）。** 6 类、每类训练 2 条、验证 1 条、测试 1 条，共 24 条区间，按拍摄日隔离；TSN R50、1 epoch、6 个训练批次。目的只有一个：确认区间读取、视频解码、训练、验证、独立测试、checkpoint 保存与结果记录全链路可运行。产物含配置、日志、checkpoint、逐样本预测、混淆矩阵与数据筛选审计。

**第二步：两个基线（2026-10-24）。** 数据来自人工标注区间：源 3,927 条，丢弃不足 60 帧 640 条、与同视频其他区间重叠 518 条、多猫标签 34 条，再用 Decord 帧校验排除 25 条越界区间，得到 2,710 条候选（activity 1,629、eating 341、drinking 164、prolonged_stationary 335、grooming 85、toileting 31、abnormal 125）。划分按事件日历日隔离、seed 1，70/22/22 天，得到 train 1,664 / val 604 / test 442。两个模型都用 Kinetics-400 预训练骨干：8 段 × 1 帧、224×224、SGD lr 0.005、warmup 2 + cosine、20 epoch、batch 16、inverse-sqrt 类别权重。选择只看验证集，规则事先固定为 macro-F1 → toileting → abnormal → grooming → drinking recall → balanced accuracy → top-1；**测试集在模型选定之后才跑**。

**第三步：四个参考骨干（2026-10-24/25）。** 数据索引、七类、按日隔离的划分与基线完全一致。四个模型分别是 VideoMAEv2-B（16 帧 × 间隔 4）、UniFormerV2-B（8 帧均匀）、X3D-S（13 帧 × 间隔 3，182px）、SlowFast-R50（32 帧 × 间隔 2），配 AMP fp16。开跑前四项预检（backbone 逐张量比对、采样帧是否落在标注区间、真实 batch 前向/反向、峰值显存）全部通过；VideoMAEv2-B 首次预检峰值 21.93 GiB 超过 21 GiB 上限，把 micro-batch 从 8 降到 4、梯度累积 4 后通过。排名在 `2026-10-25T03:16:42Z` 写入 `model_zoo_ranking.json` 冻结，之后才跑测试。

两个细节使这批对比不是严格受控：基线用 fp32、`MultiScaleCrop` 不随机裁剪、8 个稀疏帧、SGD；参考骨干用 AMP、`RandomResizedCrop`（面积 0.5–1.0）、更长的时序跨度、部分用 AdamW。跨模型的差距里混着这些差异，不能全部归给网络结构。

## 结果与分析

**链路验证通过，分数没有解释意义。** 验证集 6 条：top-1 16.67%、macro-F1 5.56%、balanced accuracy 16.67%；测试集 6 条：33.33% / 23.33% / 33.33%。每类测试只有 1 条，一个样本就能翻转一整个类别，所以这些数字只能用来说明「流程跑完了」。完整性校验（checkpoint 非空、三组索引哈希一致、拍摄日不交叉、概率有限、混淆矩阵计数正确）为 `verified`，这才是本轮真正的产出。

**两个基线：TSM 胜出，差距在 macro-F1 与 balanced。** 测试集上 TSM 79.19% / macro-F1 61.75% / balanced 65.58%，TSN 72.85% / 57.51% / 58.09%。验证集的排序一致（84.11% vs 81.62%），且 TSM 的 toileting recall 100%（support 7）。按事先规则选 TSM，这个选择没有用到测试集。

**逐类看，问题集中在两类。** TSM 的 grooming 测试 recall 只有 5.56%（18 个样本里 17 个判错，precision 25.00%），abnormal 38.89%（18 个样本），drinking 61.54%。toileting 是 100%，但 support 只有 7，不能当稳定结论。换句话讲，top-1 79% 的观感由 activity（256 个测试样本，recall 86.72%）撑起来，macro-F1 61.75% 才是七类均衡视角的真实水平。

**区间级漏检代理：TSM 20.81%，类别均衡口径 35.44%。** 前者是自然分布下 442 条里判错的比例（92/442），后者在类别均衡诊断集（79 条）上算，两个口径差 15 个百分点，说明自然分布被 activity 主导。这个数不是事件级漏检率——连续视频里动作是否被抓到、起止是否对齐，本轮没有测。

**六模型参考批次：协议选出 VideoMAEv2-B，X3D-S 在测试上略优。** 冻结排名按验证 macro-F1 排序，VideoMAEv2-B 以 70.97% 居首（X3D-S 69.33%、SlowFast-R50 66.05%、TSM-R50 63.25%、UniFormerV2-B 62.63%、TSN-R50 60.34%）。排名文件同时记了一条警告：验证集 abnormal / toileting / grooming 的 support 只有 18 / 4 / 19，macro-F1 的小差距不可靠。

测试集（442 条，排名冻结后才跑）上 VideoMAEv2-B 的 top-1 81.90% 与 abnormal recall 44.44% 是六个模型里最高的，但 macro-F1（X3D-S 69.02% vs 67.66%）、balanced accuracy（68.19% vs 63.31%）与平衡漏检代理（32.91% vs 37.97%）都是 X3D-S 更好，差距 1.4–4 个百分点。这个差距不足以推翻预设规则，也不足以宣称 X3D-S 更强——如果改用测试集挑模型，这批数字就失去留出评测的意义。记录下来的结论是：**协议选择 VideoMAEv2-B，X3D-S 作为测试上略优的第二候选，待新数据复验。**

工程上还有一条独立于指标的判断：X3D-S 峰值显存 4.19 GiB、182px、13 帧，VideoMAEv2-B 是 11.22 GiB、224px、16 帧 ViT。若要在端侧做实时推理，X3D-S 更合适；这是部署权衡，不是准确率结论。

**六个模型共同的短板。** grooming 测试 recall 全部 ≤38.89%、abnormal 全部 ≤44.44%，toileting 的测试 support 只有 7，100% 或 85.71% 都不能当稳定结论。稀有类的问题是数据量，不是模型容量。

**前期五类实验的分数容易误读，单独说清。** 在 79 段按 2 秒步长切的 4 秒片段上，三个模型的 val top-1 是 TSM 62.5%、SlowOnly 67.05%、TimeSformer 59.09%；后来的 VideoMAEv2 微调把 val 抬到 76.14%、test 81.19%。speed run 报出的 top-1 是 TSM 92.1%（93/101）、SlowOnly 91.1%、TimeSformer 81.2%，RTF 3.59–3.77。这些数字不能与本文并列：切段步长 2 秒、片段长 4 秒，相邻片段高度重叠，测试集只有 101 条，metric 天然偏高；当时也已记录「split 可能存在泄漏」。

## 结论与下一步

- 链路验证通过（TSN、24 条区间、`verified`）：证明流程可跑，不提供任何模型结论。
- 七类基线定为 TSM R50：测试集 top-1 79.19%、macro-F1 61.75%、balanced 65.58%；区间级漏检代理 20.81%（自然分布）/ 35.44%（类别均衡）。
- 六模型参考批次的协议结论是 VideoMAEv2-B（测试 top-1 81.90%）；X3D-S 在 macro-F1、balanced 与平衡漏检上更好，记为第二候选。
- 全部数字都是区间级：不能据此宣称中期目标的「准确率 75%、漏检率 10%」达成——事件级评测需要滑窗与动作定位，本轮没有做。
- 已知短板：grooming 与 abnormal 两类 recall 低；toileting support 只有 7；无猫身份，跨日同一只猫仍可能泄漏；每个模型只有一个 seed、20 epoch，没有重复实验估计方差。
- 下一步：类别不平衡与稀有类补数据；把区间级换成滑窗 + 事件合并的评测；再往后才是十类拆分（`abnormal` 拆成 scratching / gnawing / fall / seizure）与输入表示改造。

## 附录：配置与完整数据

### 环境与配置

- 模型: TSN-R50、TSM-R50（Kinetics-400 预训练）；VideoMAEv2-B、UniFormerV2-B、X3D-S、SlowFast-R50（参考批次，AMP fp16）
- 数据集: 人工标注区间 3,927 → 候选 2,710；七类；train 1,664 / val 604 / test 442
- 配置: 8 段 × 1 帧（基线）/ 16×4、8 均匀、13×3、32×2（参考）；224×224（X3D 182）；SGD 0.005 / AdamW 5e-5（VideoMAE、UniFormer）；20 epoch；有效批大小 16；inverse-sqrt 类别权重
- 运行时间戳: 2026-10-23（链路验证）、2026-10-24（两个基线）、2026-10-25T03:16:42Z（排名冻结）
- 执行入口: `scripts/prepare_cat_action_v1.py`、`scripts/train_model.py`、`scripts/run_test.py`
- 随机种子: 数据划分 seed 1；训练 seed 与配方记录在各 run 的 `run_status.json`

### 运行谱系

| 日期 | run id | 做了什么 | 执行状态 | 产物 |
| --- | --- | --- | --- | --- |
| 2026-09-15 | quadruped_cats_v1 | 79 段 4 秒切段五类实验 + 三模型 speed run（前期世代） | 完成 | `openspec/changes/archive/2026-09-15-cats-dataset-v1/`、`2026-09-15-cats-speedrun/` |
| 2026-09-10 | cats-videomaev2-finetune | VideoMAEv2-B 在 79 段五类上微调（val 76.14% / test 81.19%） | 完成 | `openspec/changes/archive/2026-09-10-cats-videomaev2-finetune/` |
| 2026-10-23 | cat_interval_smoke | TSN 六类 24 条区间链路验证 | 完成 | `results/training/cat_interval_smoke/` |
| 2026-10-24 | cat-action-v1（TSM / TSN） | 七类基线两模型训练与冻结测试 | 完成 | `results/training/cat_action_v1/{tsm_r50,tsn_r50}/` |
| 2026-10-25 | cat-action-model-zoo-v1 | 四个视频骨干参考批次；冻结排名后跑测试 | 完成 | `results/training/cat_action_v1/model_zoo_{ranking,summary}.json` |

### 完整指标与定义

两个基线的测试集与验证集。

| 模型 | val top-1 | val macro-F1 | val balanced | test top-1 | test macro-F1 | test balanced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TSM-R50 | 84.11% | 63.25% | 73.18% | 79.19% | 61.75% | 65.58% |
| TSN-R50 | 81.62% | 60.34% | 65.51% | 72.85% | 57.51% | 58.09% |

TSM-R50 测试集逐类（442 条）。

| 类别 | support | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| activity | 256 | 87.75% | 86.72% | 87.23% |
| eating | 45 | 88.37% | 84.44% | 86.36% |
| drinking | 26 | 84.21% | 61.54% | 71.11% |
| prolonged_stationary | 72 | 62.77% | 81.94% | 71.08% |
| grooming | 18 | 25.00% | 5.56% | 9.09% |
| toileting | 7 | 46.67% | 100.00% | 63.64% |
| abnormal | 18 | 50.00% | 38.89% | 43.75% |

六模型参考批次（同数据、同划分，非严格受控对比）。

| 模型 | val top-1 | val macro-F1 | test top-1 | test macro-F1 | test balanced | 平衡漏检代理 | 峰值显存 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| VideoMAEv2-B | 85.93% | 70.97% | 81.90% | 67.66% | 63.31% | 37.97% | 11.22 GiB |
| X3D-S | 82.28% | 69.33% | 80.09% | 69.02% | 68.19% | 32.91% | 4.19 GiB |
| SlowFast-R50 | 81.62% | 66.05% | 77.38% | 63.10% | 62.22% | 37.97% | 3.17 GiB |
| TSM-R50 | 84.11% | 63.25% | 79.19% | 61.75% | 65.58% | 35.44% | — |
| UniFormerV2-B | 82.95% | 62.63% | 77.83% | 56.70% | 55.65% | 41.77% | 6.45 GiB |
| TSN-R50 | 81.62% | 60.34% | 72.85% | 57.51% | 58.09% | 44.30% | — |

区间级漏检代理（测试集，按保存的逐样本预测重算，未重新推理）。

| 模型 | 自然分布（442 条） | 类别均衡（79 条） |
| --- | ---: | ---: |
| VideoMAEv2-B | 18.10%（80/442） | 37.97%（30/79） |
| X3D-S | 19.91%（88/442） | 32.91%（26/79） |
| SlowFast-R50 | 22.62%（100/442） | 37.97%（30/79） |
| TSM-R50 | 20.81%（92/442） | 35.44%（28/79） |
| UniFormerV2-B | 22.17%（98/442） | 41.77%（33/79） |
| TSN-R50 | 27.15%（120/442） | 44.30%（35/79） |

不可控差异（基线与参考骨干）。

| 维度 | TSM/TSN 基线 | 参考模型 |
| --- | --- | --- |
| 精度 | fp32 | AMP fp16 |
| 权重载入 | 只载 backbone | VideoMAE/UniFormer 同左；X3D/SlowFast 载入整个 checkpoint |
| 训练裁剪 | MultiScaleCrop + Flip + ColorJitter | RandomResizedCrop（面积 0.5–1.0） |
| 时序采样 | 8 个稀疏帧 | 16×4 / 8 均匀 / 13×3 / 32×2 |
| 优化器 | SGD 0.005 | AdamW 5e-5（VideoMAE、UniFormer）/ SGD（X3D、SlowFast） |

训练开销。

| 模型 | micro-batch × 累积 | 训练 + best-val 用时 | best epoch |
| --- | --- | ---: | ---: |
| VideoMAEv2-B | 4×4 | 3.37 h | 12 |
| UniFormerV2-B | 8×2 | 4.20 h | 14 |
| X3D-S | 16×1 | 3.28 h | 20 |
| SlowFast-R50 | 8×2 | 4.29 h | 11 |

局限：区间级评测，没有滑窗与事件合并，不能给事件级漏检率；验证集 abnormal / toileting / grooming 的 support 只有 18 / 4 / 19；toileting 测试 support 7；每模型单 seed、20 epoch，无种子方差；`abnormal` 实际以 scratching 为主，不能宣称呕吐、抽搐、跌落可识别；数据按拍摄日隔离但没有猫身份，跨日同一只猫仍可能泄漏；六模型与基线不是严格受控对比。

### 来源与核查

- 原始记录：`docs/cat_action_training_v1.md`（本文吸收其正文；该文件保留为跳转页，产物路径与哈希清单仍在其中）
- 基线产物：`results/training/cat_action_v1/{tsm_r50,tsn_r50}/`（`best_val_metrics.json`、`test_metrics.json`、`train.log`、`selection.json`）
- 参考批次：`results/training/cat_action_v1/model_zoo_{ranking,summary,preflight}.json` 与四个模型目录
- 链路验证：`results/training/cat_interval_smoke/`（`run_status.json`、`verification.json` 为 `verified`）
- 案例图：两张对照图由本报告附录表中的数字生成（环境无绘图库，脚本为一次性探针），文件名即 sha256；它们不是原始截图，只用于读表
- 指标与趋势见 metrics.json
