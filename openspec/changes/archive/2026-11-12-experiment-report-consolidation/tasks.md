# Tasks

## 1. 准备

- [x] 1.1 从 `work/pet-pipeline` 分支导入三篇报告到本分支：`teacher-detection/20261111-gdino-base-vs-tiny`、`detector-distillation/20261112-yolo11s-base-s5`、`video-data-issues/20261110-media-issues`（含 `assets/` 与不入库的 `media/`），并在 evidence 记录导入的 commit 与源分支。
- [x] 1.2 新建 `scripts/checks/check_experiment_reports.py`：遍历 `management/experiments/`，调用 `server/parsers/experiments_parser.report_problems`，打印每篇的 incomplete 原因，非零退出；对当前 11 篇跑一次，留下基线输出。

## 2. 主题 1：教师检测器选型

- [x] 2.1 合并 YOLO11 零样本体检（`archive/2026-09-10-yolo11-detection-prep/report-snapshot.md`）与 GroundingDINO Base vs Tiny（现有报告）为 `teacher-detection/20261111-teacher-selection`；正文讲清「零样本不可用 → 域内教师 → Base 取代 Tiny」。
- [x] 2.2 重写 `manifest.json` 的 evidence 六项、合并 metrics、案例收敛到 3–6 个（含夜视漏检失败案例），附录补运行谱系。
- [x] 2.3 删除被合并的旧目录，跑校验脚本确认全绿。

## 3. 主题 2：学生检测器蒸馏

- [x] 3.1 合并 Tiny 教师版（11-07）与 Base 教师版（11-12）为 `detector-distillation/20261112-student-detector`，吸收 `archive/2026-11-08-gdino-distill-yolo-detector/evidence.md` 的速度实测与失效抽样。
- [x] 3.2 一致性指标与「跨轮不可比」分开陈述（Tiny 教师版 97 天泄漏、Base 教师版 101 天泄漏、AMP 自检跳过、缺人工框 GT）。
- [x] 3.3 重写 evidence/metrics/cases，删除旧目录，跑校验。

## 4. 主题 3：语料与数据集重建

- [x] 4.1 合并早期 79 段 4 s 五类数据集、区间语料 v1（2,710 区间）、切片 v1–v8 为 `cat-data-preprocessing/20261107-slices-v8`，吸收 `archive/2026-11-07-cat-data-preprocessing/evidence.md`。
- [x] 4.2 正文写清每层损失可追溯（外延失败 18→106→143 的测量修正、多宠物计数修正回收 485 区间）、以及「85% 是可用率不是标注质量」。
- [x] 4.3 `metrics.json` 用 series 呈现可用率与片段数的版本演进；案例保留 duplicate-box、real-two-animals、seizure-two-cats 及被撤回的静物过滤反例。
- [x] 4.4 重写 evidence，删除旧目录，跑校验。

## 5. 主题 4：裁剪输入链路

- [x] 5.1 合并早期批处理三率（`results/batch/batch_report.md`）、20 段链路审计（11-03）、三臂定案与逐帧框（archive 两份 evidence）为 `cat-crop-classification/20261103-crop-pipeline`。
- [x] 5.2 写明 1/20 严格可用的原因、只训 B 臂的裁定依据，以及多宠物区间需个体跟踪的前提。
- [x] 5.3 重写 evidence/metrics/cases，删除旧目录，跑校验。

## 6. 主题 5：七类区间基线

- [x] 6.1 新建 `cat-action-v1/20261025-seven-class-baseline`：以 `docs/cat_action_training_v1.md` 为主体，并入 TSN smoke（10-23）与早期 cats_v1 的 VideoMAEv2 微调、speed run 作为「前期尝试」。
- [x] 6.2 六模型参考批次单列「协议选择 VideoMAEv2-B，X3D-S 测试略优」，并保留「不是严格受控对比」的差异表与 support 很小的警告。
- [x] 6.3 生成 metrics/cases（含 grooming recall 5.56% 的失败案例），补运行谱系与来源核查。
- [x] 6.4 `docs/cat_action_training_v1.md`、`docs/lab_cat_training_smoke.md` 改为跳转页（保留产物路径与哈希清单），更新 `scripts/README.md` 的引用，跑校验。

## 7. 主题 6：十类片段分类

- [x] 7.1 以并发改动后的最新 `cat-clip-training` 内容为基础，合并整帧臂对照、clipv9-b（11-07）、逐类错误分析（11-12）为 `cat-clip-training/20261112-ten-class-clips`。
- [x] 7.2 正文按「输入表示 → 条件准确率 → 端到端口径 → 逐类短板」组织，保留 4 轮整帧臂不可直比的说明与样本量为零的三类。
- [x] 7.3 重写 evidence/metrics/cases（图表按当前有效结论重排），删除旧目录，跑校验。

## 8. 主题 7：多宠物跟踪

- [x] 8.1 合并 v1（OC-SORT 接入）与 v2（四臂对照）为 `multi-pet-tracking/20261107-tracking-eval`，吸收 `archive/2026-11-08-multi-pet-sort-tracking/evidence.md` 与 tracker-selection 的未完成边界。
- [x] 8.2 正文讲清「碎片来自漏检而非关联」「物种抖动修好了、碎片仍超阈值」「ReID 不启用」三件事。
- [x] 8.3 重写 evidence/metrics/cases，删除旧目录，跑校验。

## 9. 主题 8：媒体数据质量案例

- [x] 9.1 在导入的 `video-data-issues/20261110-media-issues` 上补「运行谱系」与来源核查段，案例保持不变；删除 main 工作区里根级无 slug 的旧副本。

## 10. 收尾

- [x] 10.1 更新 `management/experiments/README.md`：slug 约定改为 `<YYYYMMDD>-<主题短名>`，新增「一主题一篇」「运行谱系」「数字纪律」三条。
- [x] 10.2 同步 experiment skill §5.4 与 `references/report-template.md` 的落点与命名说明。
- [x] 10.3 全仓 `rg` 检查指向已删目录/旧 slug 的引用，逐个改指或确认可忽略（archive 与历史 change 的过程记录不改）。
- [x] 10.4 跑 `check_experiment_reports.py` 与 `pytest tests/test_experiments_api.py`，两者全绿。
- [ ] 10.5 【移交】在前端 `/management/experiments` 逐篇打开 8 篇，确认章节、附录折叠、案例图与视频正常。本机未起服务，交用户复核；数据层已由 `check_experiment_reports.py` 全绿覆盖，剩余风险是排版与播放。
- [x] 10.6 在 evidence 写「数字核对清单」：每篇正文的关键数字 → 出处。
- [x] 10.7 与 main 的并发改动对齐后合并回主干（`cbaf3308`），删除 `work/experiments-reports` 分支与 worktree，并清掉 main 工作区 6 处残留（`t/`、`20261112-yolo11s-base-s5/`、旧的 `teacher-detection/20261111-gdino-base-vs-tiny/`、`video-data-issues/` 根级散件与 3 个只剩 `assets/` 的空目录）。证据：`git log --oneline -1 main`、`git worktree list`。
- [ ] 10.8 【移交】与 `work/pet-pipeline` 对齐（前置：主线推进前完成）：该分支仍有 6 个被合并掉的旧报告目录（cliperr-a、clipv9-b、yolo11s-base-s5、teacher-detection 旧名、tracking v1/v2 等）与它自己的 `cat-clip-training/20261112-videomaev2b-base-crops`。该分支合回 main 时这些路径会再次产生 modify/delete 冲突，需要按「一主题一篇」把 base-crops 并入 `20261112-ten-class-clips`，其余保留删除。

## 11. 媒体只在正文展示（2026-11-12 用户裁定：案例区不能独立成块）

- [x] 11.1 移除报告页的「案例对比」区：删除模板区块、`additionalCases`/`compareMode`/`toggleIndex`/`assetUrl`/`isVideoCase` 等状态与样式，页面只保留正文与折叠附录。验证：`npx vite build` 通过。
- [x] 11.2 八个主题报告把 cases 里的媒体按语义位置嵌入正文（案例图不再只在末尾汇总）；同期把并发会话的 `20261112-videomaev2b-base-crops` 也补齐。
- [x] 11.3 校验脚本改为双向一致：正文引用必须登记（否则 404），登记必须嵌入正文（否则读者看不到）。判据：9 篇全绿。
- [x] 11.4 同步约定与规格：`management/experiments/README.md`、experiment skill §5.4、`experiment-report-catalog` 新增「媒体只在正文展示」要求（含两条场景）。
- [x] 11.5 回归：`pytest tests/test_experiments_api.py` 8 passed；`scripts/checks/check_experiment_reports.py` 9 篇 0 incomplete。
