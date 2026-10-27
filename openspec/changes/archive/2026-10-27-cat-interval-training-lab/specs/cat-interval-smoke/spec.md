## ADDED Requirements

### Requirement: 区间内采样的数据契约

系统 SHALL 通过 `IntervalVideoDataset` 从 JSONL 索引读取 `video`、`label`、
`start_frame`、`end_frame`、`task_id`、`sample_id`，并把原标注的「1 起始、两端包含」
帧区间传给 MMAction2 标准采样链。`RestrictFrameRange` SHALL 在 `DecordInit` 之后把
`total_frames` 与 `start_index` 限定到该区间，使 `SampleFrames` 只能在区间内取帧。
帧区间超出视频实际帧数、`start_frame < 1`、`end_frame < start_frame`、空索引、绝对
路径或含 `..` 的路径 SHALL 被拒绝。索引生成过程 SHALL NOT 复制、裁剪或重编码原视频。

#### Scenario: 采样不越出标注区间

- **WHEN** 一条索引记录声明区间 `[start, end]`
- **THEN** 该样本的所有采样帧都落在 `[start, end]` 内
- **AND** 原始视频文件的字节内容与 SHA-256 保持不变

#### Scenario: 越界或非法索引被拒绝

- **WHEN** 索引中的区间超出该视频解码得到的帧数，或路径为绝对路径/含 `..`
- **THEN** 数据加载报错并指出具体行号或文件
- **AND** 该样本不会以静默截断的方式继续训练

### Requirement: 日期隔离的小样本 smoke 划分

索引生成器 SHALL 从 `datasets/cat_raw/annotations/intervals.csv` 选出六类
（`common/activity`、`common/eating`、`common/prolonged_stationary`、
`common/drinking`、`common/grooming`、`abnormal/scratching`）候选，只保留帧数
不少于 60 且与同视频内其他区间无重叠的记录，并按事件日程日（`event_YYYYMMDD`）
分组做 train/val/test 划分。每个类每个集合的配额 SHALL 为 train 2 / val 1 / test 1，
选择顺序由固定种子与 `sample_id` 哈希决定；划分种子与实际拍摄日分组 SHALL 写入审计。
同一事件日 SHALL NOT 出现在一个以上集合；候选不足时生成过程 SHALL 失败而不是静默降配。

#### Scenario: 同一拍摄日不跨集合

- **WHEN** smoke 索引生成完成
- **THEN** 任一事件日程日只属于 train、val、test 三者之一
- **AND** 审计文件记录该划分使用的种子与三个集合的拍摄日清单

#### Scenario: 重跑结果一致

- **WHEN** 在同一份源标注上以相同参数重跑生成器
- **THEN** `train.jsonl`、`val.jsonl`、`test.jsonl` 与 `classes.json` 的字节内容一致
- **AND** 若已存在不同内容的索引，生成器报错而不是覆盖

### Requirement: smoke 产物与正式基线的路径隔离

smoke 链路 SHALL 写入独立路径：索引与类别表在 `datasets/cat_interval_smoke/`，审计在
`results/training/cat_interval_smoke/data_audit.json`，配置为
`configs/cat_interval_tsn_r50_smoke.py`，运行产物在 `results/training/cat_interval_smoke/`。
`--smoke` 未启用时使用的 `datasets/cat_interval_baseline/` 与
`results/training/cat_interval_baseline/` SHALL 不被 smoke 运行读写或覆盖。
每次 smoke 运行 SHALL 记录 `run_status.json`（配置与其 SHA-256、三个索引的 SHA-256、
`torch`/`mmcv`/`mmengine`/`mmaction2`/`decord` 版本、`CUDA_VISIBLE_DEVICES`、
epoch 数、batch size、训练与测试退出码）以及 `train.log`、`test.log` 和 checkpoint 路径。

#### Scenario: smoke 不污染正式基线产物

- **WHEN** 以 `--smoke` 生成索引并运行一轮训练
- **THEN** 所有写入都落在 `cat_interval_smoke` 路径下
- **AND** `datasets/cat_interval_baseline/` 与 `results/training/cat_interval_baseline/` 无变化

#### Scenario: 运行证据可审计

- **WHEN** smoke 运行结束（成功或失败）
- **THEN** `run_status.json` 记录状态、退出码、配置与数据集哈希、环境版本
- **AND** 训练日志、测试日志、指标文件与 checkpoint 路径可在该目录内追溯到

### Requirement: 分数解释边界

smoke 结果 SHALL 只用于证明数据读取、训练、验证、测试与产物记录链路可运行。
每类仅 6 条样本（train 2 / val 1 / test 1），因此 top1、macro-F1、逐类
precision/recall/F1 与混淆矩阵 SHALL NOT 用于模型选型、模型间比较或效果外推。
运行记录与报告 SHALL 明确标注 `pipeline smoke test only`，且 SHALL NOT 以这些分数
声明准确率结论、事件级漏检率或连续时间轴验收结果。

#### Scenario: 报告标注 smoke 性质

- **WHEN** 产出的指标文件或运行摘要被引用
- **THEN** 其 purpose 字段为 `pipeline smoke test only`
- **AND** 引用处不把分数作为模型效果或选型依据

#### Scenario: 不据 smoke 分数做选型

- **WHEN** 需要决定后续训练方案或模型选择
- **THEN** 依据来自正式数据划分的验证结果
- **AND** smoke 分数不出现在选型依据中
