# speedrun-results Spec

## Purpose

SpeedRun 结果的批次化组织与筛选：每条结果记录携带 `run_name` 描述符标识所属运行批次，API 与前端页面支持按批次过滤与统计；标注视频与封面按固定目录约定落盘，保证结果可播放、有封面。

## Requirements

### Requirement: 结果记录携带 run_name

每条 SpeedRun 结果记录 SHALL 包含 `run_name` 字符串字段，标识产生该结果的运行批次。

#### Scenario: 新执行的结果带 run_name
- **WHEN** 通过 `/api/speedrun/run` 或批量脚本执行一次 speedrun
- **THEN** 该次执行产生的每条结果记录都包含相同的 `run_name`

#### Scenario: 历史结果兼容
- **WHEN** 读取的结果记录缺少 `run_name` 字段
- **THEN** 系统将其视为 `legacy` 批次，不修改磁盘上的原始记录

### Requirement: API 按 run_name 过滤

`GET /api/speedrun/results` SHALL 支持可选查询参数 `run_name`，仅返回该批次的结果。

#### Scenario: 指定 run_name 过滤
- **WHEN** 请求 `/api/speedrun/results?run_name=cats-v1`
- **THEN** 仅返回 `run_name` 为 `cats-v1` 的结果记录

#### Scenario: 不传参数返回全部
- **WHEN** 请求 `/api/speedrun/results` 不带 `run_name`
- **THEN** 返回全部结果记录（含 legacy）

### Requirement: 前端按批次筛选与统计

SpeedRun 页面 SHALL 提供「运行批次」筛选器，选项为结果中全部 `run_name` 去重值；筛选后列表、准确率、RTF、显存统计基于筛选结果计算。

#### Scenario: 选择批次查看结果
- **WHEN** 用户在 SpeedRun 页面选择某个 `run_name`
- **THEN** 结果列表仅显示该批次记录，顶部统计（准确率等）仅基于该批次计算

#### Scenario: 批次与模型/视频筛选叠加
- **WHEN** 用户同时选择 run_name 和 model_id
- **THEN** 列表与统计基于两个条件的交集

### Requirement: 标注视频落盘约定

SpeedRun 标注视频 SHALL 落盘于 `results/speedrun/outputs/<model_id>/<video_stem>.mp4`，结果记录的 `output_video` 字段 SHALL 为相对于 `results/speedrun/outputs/` 的路径（如 `tsm-resnet50/xxx.mp4`），封面图 SHALL 落盘于 `results/speedrun/outputs/covers/` 且记录 `cover_image` 字段（同为 outputs 相对路径）。

#### Scenario: 结果记录可播放
- **WHEN** 一条结果记录的 `status` 为 `completed` 且标注视频已生成
- **THEN** 通过 `/api/speedrun/outputs/<output_video>` 能获取到该视频（HTTP 200）

#### Scenario: 结果记录有封面
- **WHEN** 一条结果记录引用了标注视频
- **THEN** 该记录包含 `cover_image` 字段且对应封面文件存在

### Requirement: 前端模块归属一致

SpeedRun 页面组件 SHALL 位于与其路由模块一致的目录（`evaluation/speedrun` 路由 ↔ `views/evaluation/`），speedrun API 封装 SHALL 位于独立模块（`api/speedrun.js`）。

#### Scenario: 按模块定位代码
- **WHEN** 开发者查找 SpeedRun 页面代码
- **THEN** 在 `web/src/views/evaluation/` 与 `web/src/api/speedrun.js` 找到全部相关代码，无 training 目录残留引用

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
