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

### 2026-11-12：用户批准，开始实施（默认按建议裁定两个未决项）

- 用户回复「继续」，按建议执行：① 七类与十类拆成两篇（模型选型 vs 输入表示）；② `docs/cat_action_training_v1.md` 与 `docs/lab_cat_training_smoke.md` 转跳转页（保留产物路径与哈希清单）。
- 分支 `work/experiments-reports`，worktree `/Volumes/LEGION_PSSD/code/.worktree/experiments-reports`，基线与 main 同步一次（`b1d9fe31` → merge main，纳入标题命名规则与逐类错误分析的最新版本）。

### 2026-11-12：八篇主题报告合并完成

| 主题报告 | 合并来源 | 结论方向 |
| --- | --- | --- |
| `teacher-detection/20261111-teacher-selection` | YOLO11 零样本体检（archive report-snapshot）+ Base/Tiny 对比 | complete / improved |
| `detector-distillation/20261112-student-detector` | Tiny 教师版 + Base 教师版 + archive 蒸馏 evidence | complete / improved |
| `cat-data-preprocessing/20261107-slices-v8` | 79 段切段数据集 + 区间索引 v1 + 切片 v2/v3/v7/v8 | complete / improved |
| `cat-crop-classification/20261103-crop-pipeline` | 34 段批处理三率 + 20 段审计 + 只训 B 臂定案 + 片段级渲染 | partial / inconclusive |
| `cat-action-v1/20261025-seven-class-baseline` | 七类基线 + 六模型参考批次 + TSN smoke + 早期 cats_v1 | complete / improved |
| `cat-clip-training/20261112-ten-class-clips` | 整帧臂 + clipv9-b + 逐类错误分析 | complete / improved |
| `multi-pet-tracking/20261107-tracking-eval` | 首轮 OC-SORT + 四臂对照 + 稳定过滤 + 框细化探针 | partial / inconclusive |
| `video-data-issues/20261110-media-issues` | 现有单篇 + 全量时间戳盘点与处理范围裁定 | partial / inconclusive |

- 删除的目录：`teacher-detection/20261111-gdino-base-vs-tiny`、`detector-distillation/{20261107-yolo11s-from-gdino,20261112-yolo11s-base-s5}`、`cat-crop-classification/20261103-gdino-crop-20261103a`、`cat-clip-training/{20261107-clipv9-b,20261112-cliperr-a}`、`multi-pet-tracking/{20261107-tracking-eval-v1,tracking-eval-v2}`。共 8 个旧目录 → 8 篇主题报告（11 篇 run 级报告 + 1 篇测试残留 + 4 篇仓外历史记录）。
- 历史 change 的过程记录（`openspec/changes/pet-pipeline/*`、`web-experiment-case-picker/evidence.md`、archive）仍引用旧目录名。它们记录的是当时的证据出处，属过程留痕，不改写；本 change 只保证新报告与面向读者的文档指向现行路径。

### 2026-11-12：数字核对清单（正文关键数字 → 出处）

- 零样本 cat 检出 32.1%/32.3%、夜视漏检 89.5%/88.9%、召回代理 48.5%/48.7% → `archive/2026-09-10-yolo11-detection-prep/report-snapshot.md`
- Base 覆盖 2,723/2,737、锚点 211,413、置信度 0.45→0.68 → 原 `teacher-detection` 报告 manifest（`results/pet_pipeline/detection-versions-20261111a/detection_manifest.json`、`teacher-comparison-20261111a/comparison_report.md`）
- 学生 5.3 ms / 187.6 fps / mAP50 0.809 / 0.748 → 原 `20261107-yolo11s-from-gdino` manifest（`results/pseudo_labels/*`）
- 学生 p50 5.47 ms、mAP50 0.871 / mAP50-95 0.818、cat 0.953 / dog 0.789、4,903 秒 → 原 `20261112-yolo11s-base-s5` 报告（`results/pet_pipeline/student-train-20261112a/test-eval.log`）
- 可用率 7.6% → 85.0%、7,554 片段、多宠物 967 → 482、外延 18 → 106 → 143 → 原 `slices-v8` manifest 与 `archive/2026-11-07-cat-data-preprocessing/evidence.md`
- 34 段三率 0.939/0.905/0.334 → `results/batch/batch_report.md`
- 20 段审计 40/40、严格可用 1/20、有效帧 27.07% → 48.01% → 原 `gdino-crop` 报告（`quality/sample20*/crop_audit.json`）
- 只训 B 臂、207 区间（131/32/44）、测试 top-1 70.45%、含预处理 7.01% → `archive/2026-11-08-gdino-crop-videomaev2-evaluation/evidence.md`
- 七类 TSM 79.19% / TSN 72.85%、六模型 val 70.97% 与 test 81.90%、balanced 68.19%、平衡漏检 32.91% → `docs/cat_action_training_v1.md`（现为跳转页，原文见 `b1d9fe31`）
- 十类 top-1 85.75% / macro-F1 56.23%、端到端 72.9%、漏检 14.25%、逐类 recall、62/161 流向 activity、留一来源 85.75→86.70 与 56.4→46.4、6.7% 多窗口跨档 → 原 `clipv9-b` 与 `cliperr-a` 报告（`results/cat_clip_v9/`、`results/cat_clip_v9_analysis/`）
- 四臂碎片 4/3/3/4、稳定过滤 2、一致性 0.8182→1.0000、交换 0/16/0/0、stride2 267 秒、框细化 IoU 0.88–0.97、印刷误检 mask 0.977 → 原 tracking v1/v2 报告（`results/tracking_eval_20261107/`）
- 622 vs 627 帧、12.534 秒缺口、18 个跳跃视频、63 条排除清单 → 原 `video-data-issues` 报告（`results/pet_pipeline/annotation-overflow-review/sample-891/`）

### 2026-11-12：校验结果

- `python3 scripts/checks/check_experiment_reports.py`：8 篇全部完整，0 项 incomplete（含正文媒体引用与 manifest 登记的一致性检查）。
- `python3 -m pytest tests/test_experiments_api.py -q`：8 passed。
- 兼容性：`server/parsers/experiments_parser.py` 与前端报告页未改动；新 slug 不满足旧 `<YYYYMMDD>-<runid>` 形态，但解析器只按两级目录扫描，不受影响。
- 未做：本地页面逐篇目视（本机未起前后端）。前端读取的是同一份解析结果，风险是布局而非数据，留给用户复核。
