# speedrun-run-name Proposal

## Why

SpeedRun 结果记录（`results/speedrun/results.json`）只有 `model_id / video / checkpoint` 字段，前端筛选器只能按 model_id 或单个视频过滤。同一模型在不同批次（不同数据集、不同 checkpoint、不同目的）跑出的结果混在一起，无法区分——例如刚在 quadruped_cats_v1 上跑的 TSM/SlowOnly/TimeSformer 结果与历史 UCF101 结果共用同一 model_id，用户无法单独查看某一批次的结果。

## What Changes

- SpeedRun 结果记录新增 **`run_name`** 字段（Descriptor），标识一次运行批次（如 `cats-v1-tsm-20260814`、`ucf101-baseline`）
- 后端 `/api/speedrun/results` 支持 `?run_name=` 过滤参数
- SpeedRun 前端页面筛选区新增「运行批次」下拉框（选项从结果中的 run_name 去重生成），准确率/RTF/显存统计按筛选后数据计算
- 历史结果无 `run_name`，归入 `legacy` 批次（读取时缺省填充，不回写文件）
- 新执行的 speedrun（`/api/speedrun/run`）要求/自动生成 `run_name`，写入每条结果

## Capabilities

### New Capabilities
- `speedrun-results`: SpeedRun 结果的批次化组织与筛选（run_name 字段、API 过滤、页面批次筛选器）

### Modified Capabilities
（无基线 spec，本变更建立 speedrun-results 首个 spec）

## Impact

- **数据**：`results/speedrun/results.json` 新增 `run_name` 字段（向后兼容，旧记录缺省为 `legacy`）
- **后端**：`server/routers/speedrun.py`（results 过滤、run 接口接受 run_name）
- **前端**：`web/src/views/training/SpeedRun.vue`（筛选器 + 统计）、`web/src/api/training.js`（请求参数）
- **脚本**：批量 speedrun 脚本（如 `/tmp/speedrun_cats.py` 同类脚本）需传 run_name
