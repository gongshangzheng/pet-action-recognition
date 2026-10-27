# 设计

## 数据与过滤

源文件为 `datasets/cat_raw/annotations/intervals.csv`，3,927 条区间。按现有
协议只读读取，生成新目录 `datasets/cat_action_v1/`；原始文件、原始 JSON/CSV
副本和视频均不改动。

映射后七类：`activity`、`eating`、`drinking`、`prolonged_stationary`、
`grooming`、`toileting`、`abnormal`。`abnormal` 吸收 scratching/gnawing/
fall/seizure 四个源标签；`multi_cat_chase`、`multi_cat_roughplay` 不纳入 v1，
计数写入审计。多猫追逐/打闹后续用空间关系逻辑识别，不训练分类模型。

过滤顺序固定为：标签是否在 v1 映射 → 区间长度是否 ≥ 60 帧 → 是否与同视频
任意其他区间重叠。当前干跑计数：

| 项目 | 数量 |
|---|---:|
| 源区间 | 3,927 |
| 不足 60 帧 | 640 |
| 与同视频其他区间重叠 | 518 |
| v1 未纳入标签（多猫追逐/打闹） | 34 |
| 视频帧校验越界（Decord） | 25 |
| v1 候选 | 2,710 |

七类候选：`activity` 1,629、`eating` 341、`prolonged_stationary` 335、
`drinking` 164、`grooming` 85、`abnormal` 125、`toileting` 31。
`abnormal` 中实际可训练的主要来自 scratching；gnawing 只剩少量，
fall/seizure 过滤后为 0。`toileting` 只有 31 条候选、分布在 22 个拍摄日，
属于长尾小类。报告中必须明确这两点，不能把 `abnormal` 解释为四类异常都能
识别，也不能把 `toileting` 的少量测试结果当作稳定的验收指标。

## 划分

沿用现有 `assign_days` 的“按事件日历日分组 + 固定 seed 搜索”思想，但把规则
固定下来：

- 事件日从视频名 `event_YYYYMMDD_` 提取；无法提取时以 `video:<name>` 作为
  独立组。
- 验证/测试各取约五分之一的天数，其余为训练；搜索 seed 时要求非如厕类在
  验证/测试中至少 15 条、训练中至少 40 条；`toileting` 在验证/测试中至少
  4 条、训练中至少 10 条。
- 视频帧校验后实际得到 seed 1：70 训练日 / 22 验证日 / 22 测试日。
  自然分布候选：
  - train 1,664：activity 998、stationary 216、eating 200、drinking 93、
    grooming 48、abnormal 89、toileting 20
  - val 604：activity 375、stationary 47、eating 96、drinking 45、
    grooming 19、abnormal 18、toileting 4
  - test 442：activity 256、stationary 72、eating 45、drinking 26、
    grooming 18、abnormal 18、toileting 7
- **训练集使用上述全部候选**，不截断到每类 40 条。验证/测试保留自然分布，
  另为每个 split 生成最多 12 条/类的平衡诊断集，用于分类别召回和混淆矩阵；
  `toileting` 在验证/测试中只有 4/7 条，平衡集也只能取相同数量。
  设计期干跑为 2,735 条、seed 11、train/val/test 1,658/455/622；Decord
  越界校验排除 25 条后实际为 2,710 条、seed 1、1,664/604/442。以实际审计为准。
- `activity` 占比高，训练使用 class-weighted CE 或等价采样；权重、采样规则和
  有效样本数写入运行记录。`toileting` 作为长尾类单独记录采样权重和 support。
  验证/测试不做人为平衡。

上述计数是设计期干跑结果；apply 时由脚本重新计算并写入审计，若与设计不同，
以实际审计为准并在报告中解释差异。seed、各 split 的日期列表和所有样本 ID
都写入 `split_manifest.json`。

## 目录和产物

仓库内新增/保留：

```
configs/cat_action_tsn_r50_v1.py
configs/cat_action_tsm_r50_v1.py
scripts/prepare_cat_action_v1.py
scripts/run_cat_action_v1.py
petlib/datasets/cat_intervals.py          # 只复用，不改旧行为
docs/cat_action_training_v1.md            # 最终报告（tracked）
```

服务器/gitignored 产物：

```
datasets/cat_action_v1/
  train.jsonl
  val.jsonl
  test.jsonl
  val_balanced.jsonl
  test_balanced.jsonl
  classes.json
  label_mapping.json
  split_manifest.json
  sha256sums.txt
results/training/cat_action_v1/
  data_audit.json
  tsn_r50/{run_status.json,train.log,test.log,val_metrics.json,test_metrics.json,work/}
  tsm_r50/{...}
  selection.json
```

JSONL 字段沿用现有 `IntervalVideoDataset`：`video`、`task_id`、`start_frame`、
`end_frame`、`label`、`sample_id`。`classes.json` 是固定顺序的七类；
`label_mapping.json` 记录源标签到 v1 类的映射、未纳入标签及原因。

## 训练与模型选择

两个候选使用同一数据、同一 8 段采样（`clip_len=1, frame_interval=1,
num_clips=8`）、224×224 输入、同一增强、同一优化器和同一 epoch 数，以隔离
架构差异：

- **TSN R50**：Kinetics-400 预训练，8 段，平均分类分数。
- **TSM R50**：Kinetics-400 预训练，8 段，时序 shift。
- 训练 20 epoch（可按 early stopping 提前结束），batch 16，SGD momentum 0.9，
  warmup + cosine，weight decay 1e-4，混合精度；使用 vendored
  `CrossEntropyLoss` 的 `class_weight` 处理类别不平衡。该损失不提供
  label smoothing，本次不启用，并在报告中记录这一实现差异。
  使用 GPU 1（GPU 0 为共享占用）。
- 训练增强：interval 内采样、随机裁剪/缩放、水平翻转、亮度/对比度扰动；
  不假设所有视频都有颜色信息。评估用中心裁剪和确定性采样。
- 模型选择：以自然验证集 macro-F1 为主；若 macro-F1 接近，比较 `toileting`、
  `abnormal`、`grooming`、`drinking` 的 recall 和平衡诊断集。`toileting`
  样本少，选择时应同时看其 support，不能只看单点 recall。选择后只跑一次
  test；两个候选的 test 指标都记录，但不得回头用 test 改选择。
- 指标记录：`val_metrics.json` / `test_metrics.json` 的 `per_class` 保留七类
  完整的 support、precision、recall 和 F1；`run_status.json` 和
  `selection.json` 额外单列 `abnormal_recall_percent` 与 `abnormal_support`。
  `abnormal` 是合并类，不报告 scratching/gnawing/fall/seizure 四个子类各自的
  recall，避免让人误以为四类异常都被单独识别。
- 预训练权重先检查仓库 `checkpoints/` 是否已有；缺失时先报告，不擅自下载。
- 若两个模型都明显过拟合（训练 F1 与验证 F1 差距大），在报告中记录，不把
  “换更大模型”作为本 change 的自动动作；更大的 VideoMAE/蒸馏留给后续 change。

## 备份与记录

1. **本地**：执行前记录 `git rev-parse HEAD` 和 `git status --short`，创建
   `pre-cat-action-v1` 标签作为回滚点；只提交本 change 相关文件。`4090.txt`
   和与本 change 无关的未提交修改不得进入提交。
2. **远程**：先按 `remote-server-discipline` 记录远程 HEAD，并用 `git stash`
   保存 tracked 改动、用 `tar --null -T -` 备份会与本 change 冲突的 untracked
   文件到 `~/.pet-final-transfer/backup-<timestamp>/`；生成 manifest 后再
   同步。任何 `git clean` 只能在备份成功并核对后执行。现有远程工作树的 CRLF
   差异和未跟踪猫训练文件必须先保全，不能静默覆盖。
3. **原始数据**：记录 `intervals.csv`、原始 CSV/JSON 和视频数量/大小的
   SHA-256 或清单；派生索引只写新目录。
4. **运行**：每次训练保存配置、数据哈希、环境版本、终端日志、指标、checkpoint
   有效性和哈希；结果目录不覆盖 smoke/baseline 目录。
5. **报告**：`docs/cat_action_training_v1.md` 记录类别映射、丢弃计数、划分、
   两个模型指标、选择理由、备份位置、已知风险和未覆盖类别；同时记录多猫
   追逐/打闹后续用空间关系逻辑处理的计划。
6. **同步**：优先建立本地到 `~/pet-final` 的 Git 通道（SSH 别名/密钥），没有
   免密条件时使用已批准的 bundle/SFTP 方式；禁止在远程直接手工改文件或提交。
   同步后核对远程 HEAD 和关键文件哈希。

## 风险与边界

- `toileting` 只有 31 条候选，seed 1 下 train/val/test 为 20/4/7；验证和
  测试分别只有 4/7 条，分类别指标方差很大。v1 应报告 support，不把它作为
  稳定验收结论。
- `abnormal` 虽然合并后有 125 条候选，但实际只覆盖 scratching 为主，不能
  宣称呕吐、抽搐、跌落、持续叫可识别；这些仍需数据和单独方案。
- 验证/测试的自然分布由 `activity` 主导，准确率会被多数类拉动；必须同时
  报告 macro-F1 和分类别 recall，平衡诊断集只用于诊断。
- 按拍摄日隔离减少了同日泄漏，但没有猫身份，跨日同一只猫仍可能泄漏；本
  change 不解决身份关联。
- 多猫追逐/打闹不进入 v1；后续用空间关系逻辑（相对距离、速度、位置变化、
  停留区域等）识别，不依赖动作分类模型。
- 本 change 只做区间级分类和模型选择，不做连续视频滑窗、事件合并、时间轴
  漏检率或端侧量化；这些需要后续 change。
