# speedrun-results Spec (delta)

## ADDED Requirements

### Requirement: 自定义模型配置输入

`scripts/speedrun.py` SHALL 支持 per-model 自定义 (config, checkpoint) 对，使非 registry 权重（如自有数据集微调的 checkpoint）能走标准 speed run 管线（含黑 margin 标注、封面、落盘约定、results.json 记录）。

#### Scenario: 自定义 5 类 ckpt 跑批
- **WHEN** 以 `--custom <model_id>=<config_path>:<ckpt_path>`（可重复）指定微调模型并执行
- **THEN** 该模型按指定 config+ckpt 推理，产物与 registry 模型同格式（标注视频、封面、results.json 字段齐全）

#### Scenario: 自定义与 registry 混跑
- **WHEN** 同时传 `--models` 与 `--custom`
- **THEN** 两类模型在同一批次（同一 run_name）内执行并落盘

### Requirement: GT 标注来源

`scripts/speedrun.py` SHALL 支持 `--ann-file`（raw label 格式 `<video_path> <label_idx>`）+ `--label-map` 提供 GT：按视频 stem 匹配，命中则 `gt_label` 取 label_map 对应类名、`correct` 为预测比对结果。

#### Scenario: ann_file 命中
- **WHEN** 视频 stem 在 ann_file 中存在
- **THEN** `gt_label` 为该条目的类名，`correct` = token 归一化比对 top1

#### Scenario: 未命中回退
- **WHEN** 视频 stem 不在 ann_file 中
- **THEN** 回退现有父目录名派生 GT（UCF101 约定），无 GT 则为 None
