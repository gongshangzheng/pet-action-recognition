# Tasks

## Plan / Review

- [x] 1.1 确认第一版沿用“丢弃重叠区间、≥60 帧、按拍摄日隔离”。
- [x] 1.2 确认七类 schema：5 个常见类 + `toileting` + 合并后的 `abnormal` 类；多猫追逐/打闹排除，后续用空间关系逻辑。
- [x] 1.3 完成干跑计数、划分可行性和模型候选分析。
- [x] 1.4 生成 proposal / spec / design / tasks。
- [x] 1.5 用户 Review 本 change，并明确批准进入 Apply。

## 2. 备份与同步前置

- [x] 2.1 记录本地 `git rev-parse HEAD`、`git status --short`，创建
  `pre-cat-action-v1` 回滚标签；确认待提交内容不包含 `4090.txt`、`results/`、
  `datasets/` 或与本 change 无关的未提交文件。
- [x] 2.2 记录远程 `~/pet-final` 的 HEAD、分支和工作树状态；按
  `remote-server-discipline` 用 `git stash` 备份 tracked 改动、用
  `tar --null -T -` 备份会冲突的 untracked 文件到
  `~/.pet-final-transfer/backup-<timestamp>/`，生成 manifest 并复核。
- [x] 2.3 验证本地到 `~/pet-final` 的同步通道（SSH 别名/密钥或已批准的
  bundle/SFTP）；禁止在远程直接改文件或 `git commit`。同步前后核对远程 HEAD
  和关键文件哈希。

## 3. 标签处理

- [x] 3.1 新建 `scripts/prepare_cat_action_v1.py`：实现 v1 映射、60 帧过滤、
  同视频重叠检测、按事件日分组、seed 搜索、自然/平衡视图和审计输出；不修改
  旧的 `prepare_cat_interval_baseline.py` 和 smoke 产物。
- [x] 3.2 为映射、过滤优先级、日期解析和重复运行一致性添加最小测试
  （至少覆盖 abnormal 合并、toileting 独立成类、多猫标签排除、重叠丢弃、
  输出哈希稳定）。
- [x] 3.3 在服务器以只读源数据运行生成 `datasets/cat_action_v1/`；记录
  `intervals.csv` 运行前后 SHA-256，确认未变化。
- [x] 3.4 复核候选数、每类每 split 数量、seed 和日期无交叉；把实际审计与设计
  计数比对，差异写入 `results/training/cat_action_v1/data_audit.json`。
- [x] 3.5 生成 `classes.json`、`label_mapping.json`、`split_manifest.json`、
  `sha256sums.txt`，并把这些小文件的内容摘要记录到最终报告；大索引留在
  gitignored `datasets/`，由脚本可重建。

## 4. 模型与训练

- [x] 4.1 核对 `checkpoints/` 中的 TSN R50 和 TSM R50 Kinetics 预训练权重；
  缺失时先报告，不擅自下载或改动服务器环境。
- [x] 4.2 新建 `configs/cat_action_tsn_r50_v1.py` 和
  `configs/cat_action_tsm_r50_v1.py`：相同数据索引、8 段采样、224 输入、
  相同增强和评估指标；旧 smoke/baseline 配置保持不动。
- [x] 4.3 新建 `scripts/run_cat_action_v1.py`：支持分别跑 TSN/TSM、记录
  config/index 哈希、环境版本、日志、metrics 和 checkpoint 哈希；训练前
  `nvidia-smi` 选空闲卡，默认 GPU 1。
- [x] 4.4 在自然验证集上跑 TSN R50 与 TSM R50 各 20 epoch；记录训练/验证
  loss、macro-F1、balanced accuracy、分类别 precision/recall/F1 和混淆矩阵；
  在 `run_status.json` 单列 `abnormal_recall_percent` 与 `abnormal_support`；
  两个候选使用同一划分、同一采样和同一 early-stopping 规则。
- [x] 4.5 按“验证集 macro-F1 为主，`toileting`/`abnormal`/`grooming`/`drinking`
  recall 为辅”选择第一版模型；`toileting` 和 `abnormal` 都记录 support，在
  `selection.json` 单列 `abnormal_recall_percent`/`abnormal_support`，并记录
  选择理由和两个候选的验证指标。
- [x] 4.6 选择后只运行一次自然测试集；记录两个候选的 test 指标，但不得用
  test 结果回头修改选择或超参。

## 5. 报告、核验与同步

- [x] 5.1 生成 `docs/cat_action_training_v1.md`：七类映射、丢弃计数、划分
  清单、数据/配置/checkpoint 哈希、环境版本、两个模型指标、最终选择和已知
  风险（`toileting` 仅 20/4/7 的长尾小类、`abnormal` 只以 scratching 为主、
  未覆盖多猫/音频/稀有异常），单列 `abnormal` 整体 recall/support，并记录
  多猫追逐/打闹后续用空间关系逻辑处理。
- [x] 5.2 核验原始视频和原始标注未改动；旧 smoke 结果和旧模型 checkpoint
  未被覆盖；备份路径、manifest 和恢复步骤已记录。
- [ ] 5.3 仅提交本 change 的代码、配置、文档和 change 工件；不提交数据、
  `results/`、checkpoint、`4090.txt` 或任何凭据。
- [ ] 5.4 同步到服务器并核对远程 HEAD、派生索引哈希和报告；确认远程没有
  直接手工修改。
- [ ] 5.5 完成验收：七类索引可重建、两个模型运行记录完整、选择依据只基于
  validation、原始数据和旧资产可恢复。
