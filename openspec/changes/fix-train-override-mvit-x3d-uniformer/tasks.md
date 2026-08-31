# fix-train-override-mvit-x3d-uniformer Tasks

## 1. 修复 `_maybe_write_override`（scripts/train_model.py）

- [ ] 1.1 括号跟踪：`_in_block` 计数从只数 `()` 改为同时数 `()`/`[]`/`{}`（开符号加、闭符号减），确保 `param_scheduler = [...]` 块正确闭合
- [ ] 1.2 RepeatAugDataset 兼容：检测 base config 的 `train_dataloader.dataset.type`；非 `VideoDataset` 时 override 的 dataset dict 加 `_delete_=True`，train_dataloader 显式写 `collate_fn=dict(type='pseudo_collate')`

## 2. 验证

- [ ] 2.1 x3d-xs / uniformer-base：生成的 override 含完整 optim_wrapper（grep 确认 `type='SGD'` 或 AdamW），dry 跑过 dataset/optimizer 构建
- [ ] 2.2 mvit-small：override 含 `_delete_=True`；dry 跑过 dataset 构建（无 num_repeats TypeError）
- [ ] 2.3 回归：tsn-resnet50 生成的 override 与修复前逐字节一致（既有模型不受影响）
- [ ] 2.4 rsync 到 pet，3 个模型各跑 1 epoch 实测

## 3. 补跑与收尾

- [ ] 3.1 pet 上补跑 3 个模型的 15ep 训练 + test（沿用 cats 批量配方）
- [ ] 3.2 清理 dry/验证 run 记录，commit，更新 tasks
- [ ] 3.3 archive 本 change 及 fix-training-api-device-pretrained
