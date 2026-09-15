# fix-train-override-mvit-x3d-uniformer Proposal

## Why

cats 数据集全模型补齐测试中，3 个模型训练启动即失败（x3d-xs / uniformer-base / mvit-small），且在更早的 mammal_v0 trainall 中也从未成功过——属于训练框架 override 生成的两个既有 bug，不修复这三个模型在任何自定义数据集上都不可训。

## What Changes

两个 bug 都在 `scripts/train_model.py` 的 `_maybe_write_override`：

1. **schedule 内联解析器丢块（x3d-xs / uniformer-base）**：行解析器用括号计数跳过多行语句，但只数 `()` 不数 `[]`——`param_scheduler = [...]` 块以 `]` 收尾，`_in_block` 永远不归零，导致**其后所有行被吞**（包括 `optim_wrapper` 整块）→ 无 schedule `_base_` 的 config 内联后 optim_wrapper 缺 `type` → `KeyError: 'type'`。修复：括号计数改为同时跟踪 `()`/`[]`/`{}`。
2. **RepeatAugDataset 键泄漏（mvit-small）**：自定义数据集 override 把 `train_dataloader.dataset` 改为 `type='VideoDataset'`，但 mmengine 深合并会保留 base config 中 RepeatAugDataset 专有键（`num_repeats`/`sample_once`）→ `BaseDataset.__init__() got an unexpected keyword argument 'num_repeats'`。修复：当 base config 的 train dataset type 不是 `VideoDataset` 时，override 的 dataset dict 加 `_delete_=True`（整块替换而非合并），并显式写 `collate_fn=dict(type='pseudo_collate')` 覆盖 base 的 `repeat_pseudo_collate`。

修复后在 pet 重跑 3 个模型的 cats 训练+测试，补齐 19 模型全家桶。

不改动：已能正常训练的 16 个模型的 override 生成路径（行为不变）；不动 `_maybe_write_override` 的接口。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `training-launch-contract`：扩展 override 生成的正确性要求——无 schedule `_base_` 的 config 内联后 optim_wrapper/param_scheduler/train_cfg 必须完整；base dataset 非 VideoDataset 时 override 必须整块替换

## Impact

- **代码**：`scripts/train_model.py` 的 `_maybe_write_override`（括号计数 + 条件性 `_delete_`），预计 <30 行
- **验证**：3 个模型 dry 到 `[cmd]` + pet 实跑 1 epoch；成功后正式补跑 15ep 训练+测试
- **风险**：低——改动点均为缺陷分支；已有模型的生成产物可通过 diff 旧 override 文件回归比对
