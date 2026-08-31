# training-launch-contract Spec Delta

## ADDED Requirements

### Requirement: schedule 内联完整保留 optim_wrapper

当 base config 无 `optim_wrapper`/`optimizer`（如 x3d、uniformer 等无 schedule `_base_` 的 config）时，override 生成器内联 schedule 文件时 SHALL 完整保留 `optim_wrapper` 与 `train_cfg`、`param_scheduler` 等内容——多行语句的括号跟踪 SHALL 同时识别 `()`、`[]`、`{}`，不得以 `param_scheduler` 块未闭合为由吞掉后续行。

#### Scenario: x3d-xs 训练启动
- **WHEN** 以 x3d-xs（无 schedule `_base_`）在自定义数据集上触发训练
- **THEN** 生成的 override config 含完整 `optim_wrapper`（含 `optimizer.type`），训练进程正常进入 epoch 1，不出现 `KeyError: 'type'`

#### Scenario: uniformer-base 训练启动
- **WHEN** 以 uniformer-base 触发训练
- **THEN** 同 x3d-xs，override 含完整 schedule 三件套

### Requirement: 非 VideoDataset 的 base dataset 整块替换

当 base config 的 `train_dataloader.dataset.type` 不是 `VideoDataset`（如 RepeatAugDataset）时，override 写入的 dataset dict SHALL 使用 `_delete_=True` 整块替换（不继承 base 的专有余键如 `num_repeats`/`sample_once`），且 `train_dataloader` SHALL 显式设置与 `VideoDataset` 兼容的 `collate_fn`（`pseudo_collate`）。

#### Scenario: mvit-small 训练启动
- **WHEN** 以 mvit-small（base 用 RepeatAugDataset + repeat_pseudo_collate）在自定义数据集上触发训练
- **THEN** 构建 dataset 时不出现 `unexpected keyword argument 'num_repeats'`，训练正常进入 epoch 1

#### Scenario: 既有模型行为不变
- **WHEN** 以 base dataset 本就是 `VideoDataset` 的模型（如 tsn-resnet50）触发训练
- **THEN** 生成的 override 中 dataset dict 不加 `_delete_`，与修复前逐字节一致
