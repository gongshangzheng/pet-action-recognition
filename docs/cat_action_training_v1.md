# 猫动作训练 v1：七类标签与模型选择记录

更新日期：2026-10-24。状态：完成；TSM R50 胜出。本文指标是区间级
（clip/interval-level）结果，不是连续视频的事件级漏检率。

## 范围

第一版闭集：`activity`、`eating`、`drinking`、`prolonged_stationary`、
`grooming`、`toileting`、`abnormal`。`abnormal` 合并
`abnormal/scratching`、`abnormal/gnawing`、`abnormal/fall`、
`abnormal/seizure`。多猫追逐/打闹不进入 v1；后续计划用空间关系逻辑
（相对距离、速度、位置变化、停留区域等）识别，不依赖动作分类模型。

本版只做区间级分类与模型选择；不做连续视频滑窗、事件级漏检率或端侧量化。

## 数据与标签

源文件：`datasets/cat_raw/annotations/intervals.csv`。

- 源区间：3,927 条；原始 SHA-256
  `80da23af3c6a6db4bac739fc2c1dc8714b8b5dc063b55abe7c9762932eeb04ff`。
- 过滤：≥60 帧；与同视频任意其他区间重叠则丢弃；1-based、两端包含。
- 丢弃：不足 60 帧 640 条、重叠 518 条、多猫标签 34 条；Decord 帧校验
  再排除 25 条越界区间，最终候选 **2,710 条**。
- 类别候选：activity 1,629、eating 341、drinking 164、
  prolonged_stationary 335、grooming 85、toileting 31、abnormal 125。
- 划分：按事件日历日隔离，seed 1；70 训练日 / 22 验证日 / 22 测试日。
  - train 1,664：activity 998、eating 200、drinking 93、stationary 216、
    grooming 48、toileting 20、abnormal 89
  - val 604：activity 375、eating 96、drinking 45、stationary 47、
    grooming 19、toileting 4、abnormal 18
  - test 442：activity 256、eating 45、drinking 26、stationary 72、
    grooming 18、toileting 7、abnormal 18
- 平衡诊断集：val 76、test 79（最多 12/类，toileting 按实际 support）。
- 原始标注在生成前后 SHA-256 一致；未改原始视频/标注。

派生索引：`datasets/cat_action_v1/`（gitignored，可重建）。

```
classes.json
label_mapping.json
split_manifest.json
train.jsonl / val.jsonl / test.jsonl
val_balanced.jsonl / test_balanced.jsonl
sha256sums.txt
```

生成脚本：`scripts/prepare_cat_action_v1.py`；审计：
`results/training/cat_action_v1/data_audit.json`。

索引哈希（两个模型使用同一份）：

- train `073350c27fbda36c4a931fb0852f20a495023cfe7298e2350c677dfa9962751c`
- val `21b7bb44d8450d210bb9a73d9f951ec8e3a571ab97a79e379d5b487c6e2eb1d6`
- test `058c08bcd78554d70714533140d712c8e1db50c5398d199d711be61653d4096e`

## 备份与回滚

- 本地原始标注：`datasets/cat_raw/annotations_backup_20261024/`，
  清单 `annotations_backup_20261024.sha256`。
- 服务器原始标注：
  `/home/wyy/pet-final/datasets/cat_raw/annotations_backup_20261024/`，
  清单同名 `.sha256`。
- 本地回滚标签：`pre-cat-action-v1`（c3ed666）。
- 远程工作树备份：
  `/home/wyy/.pet-final-transfer/backup-20261024/`。
  `git stash create` 提交 `4f0b689f46487538eb02d324ff204973b95fcff3`，
  引用 `refs/backup/pet-final-pre-cat-action-v1`；
  未跟踪代码/文档 21 个文件归档为 `untracked_code.tar.gz`
  （SHA-256 `d16104349cf3215077924682a8584c0400fbc663d54a4cbe4994bba210e63dc5`）。
  排除 `.runtime/`、`weights/`、`.migration/`、datasets/results/checkpoints；
  原 `~/pet-final` 工作树未被修改。
- 训练代码通过增量 Git bundle 同步到独立 worktree
  `/home/wyy/pet-final-v1`；`datasets/`、`checkpoints/`、`results/`
  软链到原项目。原工作树仍在 `main@9847f1f`。
- 训练没有覆盖旧 smoke 结果 `results/training/cat_interval_smoke/`，也没有
  修改旧 checkpoint。

## 训练配置

- 模型：TSN R50 与 TSM R50，Kinetics-400 预训练 backbone。
- 输入：8 段 × 1 帧、224×224；训练增强随机裁剪/翻转/亮度对比度。
- 优化：SGD，lr 0.005，momentum 0.9，weight decay 1e-4，
  warmup 2 epoch + cosine，20 epoch，batch 16，8 dataloader workers。
- 类别不平衡：inverse-square-root class weights
  `[0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]`。
- 运行环境：`/home/wyy/pet-final/.runtime/pet/bin/python`
  （torch 2.1.2+cu121、mmcv 2.1.0、mmengine 0.10.7、mmaction2 1.2.0、
  decord 0.6.0、sklearn 1.7.2）。
- GPU：1 号卡；0 号卡由其他用户占用。训练结束后 GPU 1 已释放。
- 实现差异：vendored `CrossEntropyLoss` 不支持 label smoothing，
  本次未启用；类别权重生效。

预检：`results/training/cat_action_v1/preflight.json`，两套配置都能构建模型、
加载 backbone、解码 train/val/test 首样本。

配置 SHA-256：

- TSM R50 `0c36a873ce8d491dfd83a5e7ba79824cd9477ac5c7f3a803926f281255118d52`
- TSN R50 `22c0937c67cfeff16cac641f9f01c852824cf298bd7b6d66763cedfb2362f25b`

## 训练结果

运行顺序：TSM R50 → TSN R50。两个模型的 train / best-val / test 退出码均为
0，`run_status.json` 状态均为 `complete`。

### 验证集（best checkpoint，自然分布 604 条）

| 模型 | top-1 | macro-F1 | balanced acc | abnormal recall (support) | toileting recall (support) |
|---|---:|---:|---:|---:|---:|
| TSM R50 | 84.11% | 63.25% | 73.18% | 55.56% (18) | 100.00% (4) |
| TSN R50 | 81.62% | 60.34% | 65.51% | 55.56% (18) | 50.00% (4) |

### 测试集（自然分布 442 条；选择后才运行）

| 模型 | top-1 | macro-F1 | balanced acc | abnormal recall (support) | toileting recall (support) |
|---|---:|---:|---:|---:|---:|
| **TSM R50** | **79.19%** | **61.75%** | **65.58%** | **38.89% (18)** | **100.00% (7)** |
| TSN R50 | 72.85% | 57.51% | 58.09% | 33.33% (18) | 71.43% (7) |

### TSM R50（胜出）测试集分类别

| 类别 | support | precision | recall | F1 |
|---|---:|---:|---:|---:|
| activity | 256 | 87.75% | 86.72% | 87.23% |
| eating | 45 | 88.37% | 84.44% | 86.36% |
| drinking | 26 | 84.21% | 61.54% | 71.11% |
| prolonged_stationary | 72 | 62.77% | 81.94% | 71.08% |
| grooming | 18 | 25.00% | 5.56% | 9.09% |
| toileting | 7 | 46.67% | 100.00% | 63.64% |
| abnormal | 18 | 50.00% | 38.89% | 43.75% |

### 区间级漏检率代理（测试集）

从 `test_metrics.json` 的逐样本预测按平衡诊断索引重算，未重新推理。
这里的“漏检”指区间真实类别没有被预测对，不等于连续视频的事件级漏检。

| 口径 | TSM R50 | TSN R50 |
|---|---:|---:|
| 自然分布 test（442 条，micro） | 20.81% 错误 | 27.15% 错误 |
| 类别均衡 test（79 条，macro 近似） | 35.44%（51/79） | 44.30%（44/79） |
| 连续视频事件级漏检 | 未测 | 未测 |

TSM 在平衡诊断集上的分类别漏检：activity 25.00%、eating 16.67%、
drinking 33.33%、prolonged_stationary 0.00%、grooming 100.00%、
toileting 0.00%（support 7）、abnormal 58.33%。

### 产物

- TSM best checkpoint：
  `results/training/cat_action_v1/tsm_r50/work/best_macro_f1_epoch_16.pth`
  SHA-256 `1cf934fcb318dbe7cd50f2e7bcdfd2e22f425354109383dedafb9a6a9e845193`
- TSN best checkpoint：
  `results/training/cat_action_v1/tsn_r50/work/best_macro_f1_epoch_20.pth`
  SHA-256 `d75ebf54a807d804796d8a9d23362c8e958db593b36df6d2c49b359672c39b2c`
- 选择记录：`results/training/cat_action_v1/selection.json`
- 验证/测试指标与预测：
  `results/training/cat_action_v1/{tsm_r50,tsn_r50}/best_val_metrics.json`、
  `test_metrics.json`
- 训练日志：
  `results/training/cat_action_v1/{tsm_r50,tsn_r50}/train.log`、
  `best_val.log`、`test.log`、`run.log`

## 模型选择

胜出模型：**TSM R50**。

- 验证集 macro-F1：TSM 63.25% vs TSN 60.34%。
- 验证集 abnormal recall 持平 55.56%；TSM 的 toileting recall 100% vs TSN 50%。
- 验证集 balanced accuracy：TSM 73.18% vs TSN 65.51%。
- test 在 selection 之后才运行，未参与模型选择。

## 与项目验收指标的距离

- TSM 的区间级 top-1 为 79.19%，高于 75%，但这**不是**项目要求的连续视频
  事件级准确率；v1 未做滑窗/事件合并，不能据此宣称“准确率 75%、漏检率
  10%”已达标。
- balanced accuracy 65.58%、macro-F1 61.75%，类别间差异仍大。
- `grooming` 测试 recall 仅 5.56%（support 18），`abnormal` 38.89%（support 18）；
  `toileting` 100% 但 support 只有 7，不能作为稳定结论。
- 后续建议：加强类别平衡采样、补充 grooming/异常样本、加入背景/未知类，
  再做滑窗事件级评测；这些属于后续 change。

## 已知风险

- `toileting` 只有 20/4/7 条（train/val/test），验证和测试 support 很小，
  分类别指标方差大，仅作诊断。
- `abnormal` 实际以 scratching 为主，不能宣称呕吐、抽搐、跌落、持续叫可识别。
- 验证/测试自然分布由 activity 主导；必须同时看 macro-F1 和分类别 recall。
- 按拍摄日隔离减少了同日泄漏，但无猫身份，跨日同一只猫仍可能泄漏。
- v1 不覆盖多猫身份关联、音频或稀有异常独立分类。
