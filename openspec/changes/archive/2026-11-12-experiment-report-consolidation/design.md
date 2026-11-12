# Design: experiment-report-consolidation

## 1. 盘查：报告体系内外各有什么

### 1.1 已在报告体系里的（`management/experiments/`）

| 主题 | 报告目录 | 状态 / 结论 | 主要数字 |
|---|---|---|---|
| cat-clip-training | `20261107-clipv9-b` | partial / improved | 测试 1,130 片段 top-1 85.75%、macro-F1 56.23%；端到端 72.9% |
| cat-clip-training | `20261112-cliperr-a` | complete / inconclusive | 161 个错判、62 个流向 activity；scratching 漏检 43.6% |
| cat-crop-classification | `20261103-gdino-crop-20261103a` | partial / inconclusive | 20 段 40 个输出审计通过、12,174 帧无显示缺框；1/20 严格可用 |
| cat-data-preprocessing | `20261107-slices-v8` | partial / inconclusive | 区间可用率 7.6% → 85.0%（3,339/3,927），7,554 片段 |
| detector-distillation | `20261107-yolo11s-from-gdino` | partial / inconclusive | 5.3 ms/帧；对教师 mAP@0.5 0.809 |
| detector-distillation | `20261112-yolo11s-base-s5` | complete / improved | mAP50 0.871、mAP50-95 0.818；p50 5.47 ms；峰值 193.8 MB |
| multi-pet-tracking | `20261107-tracking-eval-v1` | partial / inconclusive | 碎片/个体最大 4；一致性中位 0.82 |
| multi-pet-tracking | `20261107-tracking-eval-v2` | complete / inconclusive | 一致性中位 1.00；碎片/个体最大 3 |
| teacher-detection | `20261111-gdino-base-vs-tiny`（仅 `work/pet-pipeline`） | complete / improved | Base 覆盖 2,723/2,737 视频、211,413 锚点 |
| video-data-issues | `20261110-media-issues`（仅 `work/pet-pipeline`） | partial / inconclusive | 622 帧解码 vs 容器 627 帧；最大相邻间隔 12.534 s |
| — | `t/20261102-noskeleton` | 测试残留，未入库 | 无内容，删除 |

### 1.2 报告体系之外的历史实验记录

| 来源 | 日期 | 内容 | 处置 |
|---|---|---|---|
| `docs/cat_action_training_v1.md` | 2026-10-25 | 七类区间基线（TSM/TSN）+ 六模型参考批次 + 冻结排名 | 吸收进主题 5，原文转跳转页 |
| `docs/lab_cat_training_smoke.md` | 2026-10-23 | TSN 六类 smoke（24 条，链路验证） | 吸收进主题 5，原文转跳转页 |
| `openspec/changes/archive/2026-09-10-yolo11-detection-prep/report-snapshot.md` | 2026-09-10 | YOLO11 n/s 零样本体检（79 段，夜视漏检 ~89%） | 吸收进主题 1 |
| `results/batch/batch_report.md` | 2026-09-15 | 34 段白天批处理三率（检出 0.939 / 插值 0.905 / 校正 0.334） | 吸收进主题 4（未入库产物，报告引用） |
| archive `2026-11-07-cat-data-preprocessing/evidence.md` | 2026-11-07 | 切片规则与逐层损失（activity 性质、外延失败 18→106→143） | 吸收进主题 3 |
| archive `2026-11-08-gdino-crop-videomaev2-evaluation/evidence.md` | 2026-11-04~07 | 三臂设计、漏检平滑裁剪、只训 B 臂定案 | 吸收进主题 4 |
| archive `2026-11-08-clip-box-crop-input/evidence.md` | 2026-11-07 | 逐帧框、离线渲染、跟踪脚本改名 | 吸收进主题 4 |
| archive `2026-11-08-cat-clip-ten-class-training/evidence.md` | 2026-11-07 | 整帧臂 4 轮后由守卫终止 | 吸收进主题 6（作为对照臂） |
| archive `2026-11-08-gdino-distill-yolo-detector/evidence.md` | 2026-11-07 | 速度实测、失效抽样、20/30 轮中止 | 吸收进主题 2 |
| archive `2026-11-08-multi-pet-sort-tracking/evidence.md` | 2026-11-07 | OC-SORT 接入、四臂指标、ReID 判定 | 吸收进主题 7 |
| archive `2026-11-08-multi-pet-track-cropping`、`2026-11-08-tracker-selection` | 2026-11-08 | 移交与未完成边界 | 只作边界说明引用（主题 4、7） |
| archive `2026-09-15-cats-dataset-v1`、`2026-09-10-cats-videomaev2-finetune`、`2026-09-15-cats-speedrun`、`2026-10-27-cat-interval-training-lab` | 2026-09~10 | 早期 79 段 4 s 五类数据集、VideoMAEv2 微调（val 76.14% / test 81.19%）、三模型 speed run（RTF 3.59–3.77）、TSN smoke | 吸收进主题 3（语料）与主题 5（基线）的「前期尝试」 |
| archive `2026-10-27-benchmark-animalkingdom-mammal` | 2026-10-27 | 迁移数据集 mammal_v0 的模型对比 | 不吸收，主题 5 附录一行引用 |
| archive `2026-09-15-multi-object-detect-gate` | 2026-09-15 | 多 prompt 检测 + 空间状态规则 | 不吸收（属空间状态，归 `pet-system-integration`） |
| `docs/company_*.md`（7 份） | 2026-09~10 | 公司服务器环境、离线资产、标注审计、视频路径 | 不吸收（不是动作识别实验，仍是独立运维记录） |
| `management/docs/*.md` | — | wiki（models、training-guide、datasets、lessons） | 不吸收，保持索引角色，需改指处按需改 |

## 2. 目标：8 篇主题报告

每篇的主题、合并来源与预期结论方向如下。`status` / `verdict` 是**待核对的初稿**，以合并时每篇的证据为准，不得为了好看改写。

### 主题 1：教师检测器选型（`teacher-detection/20261111-teacher-selection`）

- 合并：YOLO11 零样本体检（09-10）、GroundingDINO Base vs Tiny（11-11）。
- 要讲清的链条：COCO 零样本在本域不可用（cat 检出 32%、夜视漏检约 89%）→ 必须域内教师 → Tiny 覆盖不全、暗光漏检 → Base 覆盖 2,723/2,737 视频、211,413 锚点，成为正式教师。
- 初稿：complete / improved。
- 边界：Base 的「更好」是同帧目视 + 覆盖统计，没有人工框 GT 的量化召回率。

### 主题 2：学生检测器蒸馏（`detector-distillation/20261112-student-detector`）

- 合并：Tiny 教师版（11-07）、Base 教师版（11-12）、archive 蒸馏 evidence。
- 链条：教师慢（约 150 ms/锚点）→ 伪标签蒸馏 yolo11s@1280 → 5.3 ms/帧，对教师 mAP@0.5 0.809（Tiny 教师）→ 换 Base 教师 + 只读共享 split 重做，mAP50 0.871。
- 初稿：complete / improved。
- 边界：指标是对教师伪标签的模仿度，不是真实准确率；101 个事件日跨 split 泄漏；缺人工框 GT。

### 主题 3：语料与数据集重建（`cat-data-preprocessing/20261107-slices-v8`）

- 合并：早期 79 段 4 s 五类数据集（09-15）、区间语料 v1（2,710 区间）、切片 v1–v8（11-07 evidence + v8 报告）。
- 链条：整段 clip 方案在 79 段单日单机位语料上不可扩展 → 改按标注区间切片 → 检测只覆盖 2,144 段、多宠物计数错判 → 补检测 + 修多宠物规则 → 3,339/3,927 可用、7,554 片段。
- 初稿：complete / improved（round 8 定版；原报告的 partial 是因为把训练进展混进来了，训练归主题 6）。
- 边界：85% 是「能切片」的可用率，不等于标注质量或类间平衡达标。

### 主题 4：裁剪输入链路（`cat-crop-classification/20261103-crop-pipeline`）

- 合并：早期批处理三率（09-15）、20 段链路审计（11-03）、三臂设计到只训 B 臂的定案（archive 11-08）、逐帧框与离线渲染（archive clip-box-crop-input）、多宠物裁剪切分（archive multi-pet-track-cropping）。
- 链条：跟拍裁剪能跑通（34 段三率）→ GroundingDINO 定位后裁剪（20 段审计）→ 三臂（原视频 / 纯裁剪 / 裁剪 + 像素运动）定案只训 B → 逐帧框 + 离线渲染成为训练输入。
- 初稿：partial / inconclusive（人工画面稳定性未确认，20 段仅 1/20 严格可用）。
- 边界：本轮不回答准确率提升；多宠物区间仍需个体跟踪才能确定裁谁。

### 主题 5：七类区间基线（`cat-action-v1/20261025-seven-class-baseline`）

- 合并：TSN smoke（10-23）、七类 TSM/TSN（10-24）、六模型参考批次（10-25）、早期 cats_v1（09-10）的 VideoMAEv2 微调与 speed run 作为前期。
- 链条：先验链路能跑（smoke，24 条无解释力）→ 七类区间基线 TSM 79.19% / TSN 72.85%（442 条测试）→ 六模型参考批次，协议选出 VideoMAEv2-B（81.90%），X3D-S 在测试上略优但按协议不改。
- 初稿：complete / improved。
- 边界：区间级、非事件级；grooming / abnormal 两类 recall 低；六模型不是严格受控对比（精度、增强、采样各不相同）。

### 主题 6：十类片段分类（`cat-clip-training/20261112-ten-class-clips`）

- 合并：整帧臂（4 轮，top-1 75.95%）作为对照、clipv9-b（11-07）、逐类错误分析（11-12 及并发改动的最终版本）。
- 链条：整帧输入猫只有十几像素 → 按轨迹裁剪片段 → 测试 85.75% / 端到端 72.9% → 逐类拆解错误来源（activity 吸附 62/161、scratching 漏报是可见性问题、误报是标注口径边界）。
- 初稿：complete / improved。
- 边界：gnawing 4 条、fall / seizure 0 条测试样本无法评估；区间级漏检 13.94%，未达 10%。

### 主题 7：多宠物跟踪（`multi-pet-tracking/20261107-tracking-eval`）

- 合并：v1（OC-SORT 接入）、v2（四臂对照）、archive 四臂 evidence、tracker-selection 未完成边界。
- 链条：原管线取最高分框、多宠物同框静默跳变 → OC-SORT 与 SORT 基线逐帧等价（碎片来自漏检不是关联）→ 修物种抖动与幻影轨迹（一致性中位 0.82 → 1.00）→ 碎片/个体最大 3 仍超阈值 2，ReID 不启用。
- 初稿：partial / inconclusive。
- 边界：标注无身份字段；采样 stride=5 的稀疏观测是上限约束之一。

### 主题 8：媒体数据质量案例（`video-data-issues/20261110-media-issues`）

- 合并：现有单篇（从 `work/pet-pipeline` 导入规范 slug 版）。
- 保持案例核查定位，只补「运行谱系」与来源核查段。

## 3. 合并规矩

### 3.1 目录与 slug

- 一主题一篇：`management/experiments/<topic>/<YYYYMMDD>-<主题短名>/`。
- `<YYYYMMDD>` 取该主题**最后一轮**实验日期；`<主题短名>` 说明对象与问题，不再表示单次 run。
- 原 `t/` 测试残留与 `video-data-issues/` 根级无 slug 形态一并清除。

### 3.2 frontmatter

- `run_id`：该主题最新一轮的 run id（保持后端正则与排序不变）。
- `status`：主题内各轮的合并执行状态——全部完成取 `complete`，任一未完成取最差者，并在 summary 指明是哪一轮。
- `verdict`：主题最新一轮的结论方向。
- `summary`：结论的一句话摘要，必须同时包含「做到了什么」与「没证明什么」。
- `source`：主产物路径；其余产物在附录「运行谱系」列出。

### 3.3 正文

- 六章齐全，标题格式「<主题>：<对照方案与评估目标>」，不预设结论。
- 「结果与分析」按**子问题或轮次**组织，不按 run 目录顺序堆料；每段结论就近给数字，并说明该数字测的是什么、不测什么。
- 合并后正文只保留能帮助判断的数值；完整表格、逐轮配置、命令、哈希进附录。
- 每篇正文至少写一节该主题的失败边界（失败案例、失效条件、样本量为零的类别）。

### 3.4 附录：运行谱系

每篇新增「运行谱系」表，列为：日期 / run_id / 做了什么 / 执行状态 / 产物路径。这是版本信息唯一的落点，正文不再按版本叙述。

### 3.5 指标与案例（`metrics.json` / `manifest.json`）

- `metrics`：跨轮合并去重；同一指标不同轮次保留两条，`limitation` 写明轮次与不可比原因（如整帧臂只跑 4 轮）。
- `metrics.json` 的 `series` 用于主题内的演进（可用率 v1→v8、对教师一致率 Tiny→Base、跟踪一致性 v1→v2），`tables` 放当前有效结论表。
- `cases`：每主题 3–8 个，跨轮去重；必须含至少 1 个失败案例。`selection_reason` 写选择规则，不写「效果好」。
- 图片进 `assets/`（<1 MB），视频进 `media/`（H.264 <10 MB，不入 Git）；合并时按现有 sha256 文件名原样复制，不重新编码。
- `evidence` 六项按主题粒度重写：`实验类型` 可写「多轮：感知质量 + 性能」这类组合，`样本量` 写清是哪一轮的哪一批。

### 3.6 数字纪律

- 每个数字必须能在本报告引用的 `source` 或来源文档里找到原值；合并只做搬运与对齐，不重算。
- 跨轮不可比的（整帧臂 4 轮 vs 20 轮、Tiny 教师 vs Base 教师）单列一行说明，不放进同一张对比表当结论。
- 已知被推翻的旧结论保留「对旧结论的更正」小节，不静默删除。

## 4. 历史文档处置

| 文档 | 处置 | 理由 |
|---|---|---|
| `docs/cat_action_training_v1.md` | 正文迁入主题 5，原文件改为 5 行跳转页，保留产物路径与 checkpoint/索引哈希清单 | archive 的 design/evidence 与 `scripts/README.md` 仍在引用该路径 |
| `docs/lab_cat_training_smoke.md` | 同上，迁入主题 5 的「前期尝试」 | 同上 |
| archive 下所有 `evidence.md` / `report-snapshot.md` | 不动 | 归档件不可变，报告在附录引用路径 |
| `results/batch/batch_report.md` | 不动（未入库产物） | 报告以 `source` 引用 |
| `management/docs/*.md` | 仅改需要改指的引用 | wiki 保持索引角色，不与报告双写 |

## 5. 校验

1. `python3 scripts/checks/check_experiment_reports.py`：逐篇跑 `report_problems`，任何 `incomplete` 或缺章节即非零退出；合并后 8 篇必须全绿。
2. 人工核对：逐篇把正文数字与来源报告/文档对照一遍，列出核对清单（数字 → 出处）在 evidence。
3. 页面检查：`/management/experiments` 侧栏 8 篇可读，附录折叠正常，案例图与视频可播放（既有前端不动）。
4. 引用检查：`rg` 全仓确认没有指向已删目录的链接。

## 6. 执行顺序与提交粒度

1. 导入 `work/pet-pipeline` 的三篇报告（含媒体文件），先让本分支拥有全部素材。
2. 一个主题一篇提交：`docs(experiments): <主题>合并`；每篇完成后立刻跑校验脚本。
3. 汇总提交：README 与 skill 约定同步、`docs/` 两份转跳转、校验脚本入库。
4. `evidence.md` 每完成一篇追加一条（做了什么 + 关键数字 + 未决）。

## 7. 风险与未决

- **并发改动**：本分支基线 `main@b1d9fe31`，报告页那边仍在改 cat-clip-training 的逐类错误分析（12:33 还有提交）。主题 6 合并时以并发改动的最终版本为准，合并回主干前 rebase 并重核数字。
- **跨分支素材**：三篇报告只存在于 `work/pet-pipeline`；若该分支后续改动这些报告，需要再同步一次。
- **未入库残留**：main 工作区还有 `t/`、`video-data-issues/` 根级、`teacher-detection/`、`detector-distillation/20261112-yolo11s-base-s5/` 四份未入库副本；本分支入库规范版后需在 main 工作区删除，避免两套并存。
- **未决（需用户裁定）**：主题 5（七类）与主题 6（十类）是否算同一主题。本设计按「两个独立问题（模型选型 vs 输入表示）」分为两篇；若要求合成一篇，报告会明显变长，且选型与输入表示的对照会混在一起。
- **未决（需用户裁定）**：`docs/cat_action_training_v1.md` 是转跳转页还是整文件删除。转跳转页的代价是仓库里多两个占位文件。
