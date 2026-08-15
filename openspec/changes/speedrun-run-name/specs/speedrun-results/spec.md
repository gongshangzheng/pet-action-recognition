# speedrun-results Spec

## Purpose

SpeedRun 结果的批次化组织与筛选：每条结果记录携带 `run_name` 描述符标识所属运行批次，API 与前端页面支持按批次过滤与统计。

## ADDED Requirements

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
