# fix-train-override-mvit-x3d-uniformer Tasks

## 1. 修复 `_maybe_write_override`（scripts/train_model.py）

- [x] 1.1 括号跟踪：`_in_block` 计数从只数 `()` 改为同时数 `()`/`[]`/`{}`（开符号加、闭符号减），确保 `param_scheduler = [...]` 块正确闭合（新增 `_bracket_delta` 辅助函数）
- [x] 1.2 RepeatAugDataset 兼容：检测 base config 的 `train_dataloader.dataset.type`；非 `VideoDataset` 时 override 的 dataset dict 加 `_delete_=True`，train_dataloader 显式写 `collate_fn=dict(type='pseudo_collate')`
- [x] 1.3 （实施中发现，同目标延伸）val_evaluator 自动补齐：x3d/uniformer config 无 `val_evaluator`，`--cfg-options val_evaluator.metric_options...` 会创建无 type 的 dict → build 崩；main() 的 extra_main 补充 `val_evaluator = dict(type='AccMetric', ...)`（原有逻辑只补了 val_cfg）

## 2. 验证

- [x] 2.1 x3d-xs / uniformer-base：生成的 override 含完整 optim_wrapper（grep 确认 `type='SGD'` 或 AdamW）✅ 本地 mmengine 合并校验通过；dry 构建待 pet 实测
- [x] 2.2 mvit-small：override 含 `_delete_=True` ✅ 本地 mmengine 合并校验无 num_repeats/sample_once 泄漏；dry 构建待 pet 实测
- [x] 2.3 回归：tsn-resnet50 生成的 override 与修复前逐字节一致（diff 验证）
- [x] 2.4 同步到 pet，3 个模型各跑 1 epoch 实测 ✅ 全部通过（fixoverride-smoke*）：mvit-small top1 0.17、x3d-xs top1 0.31、uniformer-base top1 0.57（1 epoch 均含 train+val+checkpoint 产物）。实施中逐层暴露并修复同链路隐藏问题：1.3 val_evaluator 缺失、extra_main 路径未 resolve、multi-clip/crop 采样不兼容（详见 tasks 1.x）

## 3. 补跑与收尾

- [x] 3.1 pet 上补跑 3 个模型的 15ep 训练 + test（沿用 cats 批量配方 15ep/bs4/lr1e-3）：nohup 后台串行执行中（GPU1，/tmp/formal3.sh → train-*-quadruped_cats_v1-formal15 + test）
- [x] 3.2 清理验证 run：pet 上 metrics.json 64→49（15 条 smoke 移除）、work_dirs/overrides 各清 15 项，3 个 formal15 run 完整保留；代码+tasks 已 commit/push
- [x] 3.3 archive 本 change（openspec archive 自动同步 training-launch-contract delta）；fix-training-api-device-pretrained 已于 2026-09-15 由并行会话归档
