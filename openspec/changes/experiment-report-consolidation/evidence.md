# 证据

### 2026-11-12：报告体系盘点（开工前只读核查）

- **范围**：`management/experiments/` 全部目录、`docs/` 下两份实验记录、`openspec/changes/archive/` 下 18 个实验类 change、`results/batch/batch_report.md`。
- **现状**：`main@b1d9fe31` 上有 8 个主题 7 篇报告；`work/pet-pipeline` 另有 3 篇（teacher-detection、detector-distillation Base 教师版、video-data-issues 规范 slug 版）。逐篇跑 `report_problems` 的结果：7 篇 narrative 模板且无 incomplete；`t/20261102-noskeleton` 缺章节（测试残留，未入库）。
- **仓外素材**：`docs/cat_action_training_v1.md`（360 行，七类 + 六模型）、`docs/lab_cat_training_smoke.md`（10 行 smoke）、`archive/2026-09-10-yolo11-detection-prep/report-snapshot.md`（YOLO11 零样本体检）、上述 8 份实验证据记录。
- **作坊环境**：新建 worktree `/Volumes/LEGION_PSSD/code/.worktree/experiments-reports`，分支 `work/experiments-reports`，基线 `main@b1d9fe31`，不影响正在进行的其它会话。
- **并发事实**：盘点期间 main 上仍有新提交（`e8cfb2e2`、`b1d9fe31`，12:33），主题 6 的合并必须以并发改动最终版本为基础。

### 2026-11-12：方案待用户审定

- 合并为 8 篇主题报告，方案见 design.md 第 2 节。
- 两个未决项请用户裁定：① 七类与十类是否算同一主题；② `docs/cat_action_training_v1.md` 转跳转页还是删除。
