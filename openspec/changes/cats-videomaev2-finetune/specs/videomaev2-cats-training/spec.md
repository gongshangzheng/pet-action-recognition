# videomaev2-cats-training Spec Delta

## ADDED Requirements

### Requirement: 训练 registry 包含 videomaev2-base

`GET /api/training/models` SHALL 返回 `id` 为 `videomaev2-base` 的模型条目，其 `mmaction2_config` 指向仓库根下的 `configs/cats_videomaev2_base_16x4.py`，`pretrained_url` 指向 K710 蒸馏权重。

#### Scenario: web 训练页可选模型
- **WHEN** 请求 `/api/training/models`
- **THEN** 模型列表包含 `videomaev2-base`，且其配置路径可被 `resolve_mmaction2_config` 解析为存在的文件

### Requirement: config 自带 backbone 预训练初始化

`configs/cats_videomaev2_base_16x4.py` 的 backbone SHALL 声明 `init_cfg = Pretrained(prefix="backbone.")`，训练启动时不传任何训练模式标志（pretrained/load_from/from_scratch）即可从本地 K710 ckpt 加载 backbone 权重；cls_head 为 5 类随机初始化。

#### Scenario: 默认模式启动训练
- **WHEN** 以 model_id=videomaev2-base、dataset_id=quadruped_cats_v1、不传 pretrained 触发 `/api/training/run`
- **THEN** 训练正常启动，日志无 cls_head 形状冲突错误

#### Scenario: checkpoint 缺失时给出可读错误
- **WHEN** 本地 `checkpoints/videomaev2-base/` 下不存在任何 `.pth` 权重且训练被触发
- **THEN** 训练在启动阶段失败，错误信息指明缺失的 checkpoint 路径

### Requirement: 训练指标按契约落盘

训练 run SHALL 在 `results/training/metrics.json` 生成记录：`model=videomaev2-base`、`dataset=quadruped_cats_v1`、status 与 val top1 指标随训练更新；产物 checkpoint 位于 `results/training/work_dirs/<run_id>/`。

#### Scenario: 训练完成后查询指标
- **WHEN** 训练 run 结束（completed 或 error）
- **THEN** `metrics.json` 中该 run 的记录包含最终 val top1（或 error 说明），web 训练结果页可见该 run
