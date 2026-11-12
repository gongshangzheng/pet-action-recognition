# Proposal: experiment-report-consolidation

## Why

实验报告体系当前是「一次 run 一篇」：`management/experiments/` 下 8 个主题有 11 篇报告（其中 3 篇只存在于 `work/pet-pipeline` 分支），同一主题的多轮实验各自成篇，读者要读完 v1、v2 才知道这条线到底做了什么、得到什么结论。同时更早的实验结果散在报告体系之外：`docs/cat_action_training_v1.md`（七类区间基线 + 六模型参考批次）、`docs/lab_cat_training_smoke.md`（训练链路流程验证）、`openspec/changes/archive/*/evidence.md`（裁剪、跟踪、蒸馏、十类训练的过程记录）、`results/batch/batch_report.md`（早期批处理三率），以及 `report-snapshot.md`（YOLO11 零样本体检）。这些内容不进报告页，读者没有入口，时间一长就无法说明每一步做了什么。

用户 2026-11-12 裁定：**同一主题只要一篇**，版本信息不重要，重点是按主题讲清「做了什么实验、得到什么结果」。本 change 执行这次合并。

## What Changes

- `management/experiments/` 从 11 篇 run 级报告合并为 **8 篇主题报告**，每篇覆盖该主题全部轮次；报告正文按「背景与目标 / 当前问题 / 实验设计 / 结果与分析 / 结论与下一步 / 附录」组织，附录收「运行谱系、完整指标、来源与核查」。
- 把报告体系之外的实验记录吸收进对应主题报告：七类区间基线与六模型参考批次、训练链路流程验证、YOLO11 零样本体检、早期批处理三率、裁剪/跟踪/蒸馏/十类训练的过程结论。
- 报告目录命名从 `<YYYYMMDD>-<runid>` 改为 `<YYYYMMDD>-<主题短名>`，`run_id` 保留该主题最新一轮，全部 run 的谱系写进附录；`management/experiments/README.md` 与 experiment skill 同步这条约定。
- 新增 `scripts/checks/check_experiment_reports.py`：调用 `server/parsers/experiments_parser.report_problems` 逐篇校验，`incomplete` 即失败退出，供合并后与今后每篇新报告使用。
- 被吸收的 `docs/cat_action_training_v1.md`、`docs/lab_cat_training_smoke.md` 改为指向报告的跳转页（保留路径与产物哈希清单，避免 archive 中的引用断链）。
- 从 `work/pet-pipeline` 分支导入三篇只存在于该分支的报告（teacher-detection、detector-distillation Base 教师版、video-data-issues 规范 slug 版），合并进本分支的主题报告。

## Capabilities

### New Capabilities

- `experiment-report-catalog`：主题级报告的目录与合并约定（一主题一篇、合并报告须交代各轮做了什么与结论、被吸收的历史文档保留跳转、校验脚本可判定完整度）。

### Modified Capabilities

无。`experiments-report-layout` 只约束页面布局，本次不改前端。

## Impact

- 受影响目录：`management/experiments/`（结构重排）、`docs/`（两份转为跳转）、`.claude/skills/experiment/`（§5.4 与 README 约定同步）、`scripts/checks/`（新增校验脚本）。
- 不受影响：`server/parsers/experiments_parser.py` 与前端报告页（继续按目录扫描，无需改动）；`management/docs/*.md` wiki（保持索引角色，仅按需改指）。
- 风险：本分支基线是 `main@b1d9fe31`，而 `work/pet-pipeline` 分支另有 3 篇报告与相关代码；合并回主干前需与并发中的逐类错误分析改动对齐。
