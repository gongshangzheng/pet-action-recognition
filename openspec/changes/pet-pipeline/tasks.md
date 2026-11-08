## 1. 检测

### 1.1 现状与已有实现

- [x] 1.1.1 检测入口与实现位置：`scripts/prepare_cat_crop_experiment.py --stage detect`；核心函数 `detect_video`（逐视频顺序解码、每 `sample_stride` 帧推理一次）、`run_detect`（遍历视频、写缓存）、`load_reusable_detection`（复用前校验）。证据：该文件 139/208/1042 行。
- [x] 1.1.2 补检测 429 段：`scripts/remote/run_missing_detection.sh` 对未检测视频跑检测，覆盖达 2,573 段（2,144 + 429），rc=0、4,532 秒。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.1.3 检测产物结构：`assets/full_run/detections/<stem>.json`，schema `cat-crop-detection-v2`，含 `anchors`（帧号 → 候选框、猫/狗计数、目标框）、`sample_stride`、`decoded_frames`、`fingerprint`、`source_sha256`。证据：同目录任一缓存。
- [x] 1.1.4 多宠物锚点被记为 `source=invalid`：统计多宠物必须读 `anchors` 原始计数，按 `source=="detected"` 过滤会得到 0（此坑踩过两次）。证据：`archive/2026-11-07-cat-data-preprocessing/evidence.md`。
- [x] 1.1.5 `decoded_frames` 可能大于播放器实际帧数：导出训练标注时必须逐视频探测并 clamp，否则出现 `Interval [1119,1178] exceeds 1031 frames`。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。

### 1.2 检测指纹是什么、用在哪

- [x] 1.2.1 指纹内容与生成函数：`model_fingerprint()`（权重 `weights_sha256`、字节数、`config_sha256`）与 `detection_fingerprint_for_args()`（再加 `classes=["cat","dog"]`、`sample_stride`、`box_threshold`、`text_threshold`）合成一份指纹，写在每个检测缓存的 `fingerprint` 字段。位置：`scripts/prepare_cat_crop_experiment.py:195` 与 `:310`。
- [x] 1.2.2 指纹的用途：`load_reusable_detection()` 在复用缓存前，比对源视频 SHA-256 与当前指纹；不一致即拒绝复用，避免用不同权重/阈值/步长产生的旧检测冒充新结果。这也是“改了检测参数必须重新检测”的强制点。
- [x] 1.2.3 索引阶段的二次校验：`interval_availability()` 用 `detection_fingerprint_for_args()` 生成期望指纹，与缓存里的指纹不一致就把该区间判为不可用（`detection_cache_unavailable`）。

### 1.3 待办：视频清单与脚本合并

- [x] 1.3.1 建立单一视频清单：把源索引（`cat_action_v1` 的 train/val/test）与现有散落列表（`all_videos.txt` 2,144 行、`tmp/detect_missing_videos.txt` 429 行）合并成一份 `videos.jsonl`，每条记录视频路径、所属 split、区间数、检测状态、渲染状态、跟踪状态。判据：清单行数等于带标注视频数（2,573），三类状态字段齐全，抽样 20 行与磁盘一致。已完成：`results/cat_pipeline/videos.jsonl` 2,573 行（in_index 2,144、detected 2,573、rendered 1,981、tracked 2,335）。
- [ ] 1.3.2 取消“允许索引外视频”的例外：改为从 1.3.1 的清单驱动检测，删除 `selected_videos` 里“显式列表可含索引外视频”的分支与 `--video-list` 参数。判据：检测阶段的输入只剩清单路径，且 2,573 段全部可被选中。
- [ ] 1.3.3 合并检测脚本：现存三个入口 `scripts/prepare_cat_crop_experiment.py --stage detect`、`scripts/pet_detect_track.py`、`scripts/pet_multi_detect.py`。保留前者作为唯一入口，把后两者中仍需的能力（如逐帧轨迹、批量重试）迁入或标注废弃。判据：`grep -rn "pet_detect_track\|pet_multi_detect"` 只出现在归档文档中，检测相关测试全绿。
- [ ] 1.3.4 清单驱动的状态汇总：按 1.3.1 的清单输出“多少个视频已检测/已渲染/已跟踪/三项齐全”。判据：四个计数写入 evidence，且与 `assets/full_run` 实际文件数一致。

### 1.4 待办：检测器可替换（GDINO-tiny → base / 自训 YOLO）

用户提示：现在用 GroundingDINO-tiny，后续可能换成 GDINO-base，也可能换成自己重训的 YOLO。要求检测层不绑死在某一个模型上。

- [ ] 1.4.1 泛化指纹字段：现指纹写死 `classes=["cat","dog"]` 与 GDINO 的 `box_threshold`/`text_threshold`；改为 `model_family`（gdino-tiny / gdino-base / yolo-custom）+ `weights_sha256` + **任意参数字典**（由各检测器自己声明），不预设阈值名称。判据：指纹结构写入 evidence，旧缓存因缺少 `model_family` 被判为不可复用（等权重）。
- [ ] 1.4.2 缓存 schema 记录检测器身份与参数：`detections/<stem>.json` 增加 `detector` 段（family、weights、params），并在读取时校验。判据：抽样 3 份缓存字段齐全；参数改动后复用被拒。
- [ ] 1.4.3 YOLO 适配器接口预留：`petlib/detection/base.Detector.detect(img, classes)` 已存在；补一个 `YoloDetector` 空实现或说明文档，明确输入（BGR 图）、输出（`Detection` 列表，含 class/box/confidence）、批处理与阈值参数从 `params` 读。判据：接口与方法签名写入 design，未实现部分标注 TODO。
- [ ] 1.4.4 切换检测器时的重检策略：给出规则——权重、family 或任一参数变化即触发全量重检；仅 `sample_stride` 变化可复用逐帧候选但需重采样。判据：规则写入 evidence；用一次假参数变更验证缓存被拒。
- [ ] 1.4.5 检测器对比实验（条件）：若换用 base 或 YOLO，在 30 段含小目标/夜间/多宠物的视频上比对检出率与重复框比例，判据：对照表写入 evidence；不换则不执行。

### 1.5 待办：检测目录按检测器分隔

- [ ] 1.5.1 检测产物改为按检测器分目录：`assets/detections/<family>__<stride>/`（如 `gdino-tiny__s5`），每目录一份 `manifest.json` 记录完整指纹与完成数。判据：现有 2,573 份缓存可被无歧义归入某一目录，抽样 5 个目录读出指纹一致。
- [ ] 1.5.2 索引与片段清单记录所用检测目录与指纹哈希。判据：清单里每条片段能追溯到唯一检测目录；换目录后旧清单不被静默覆盖。
- [ ] 1.5.3 按区间取框的接口落到 petlib：`boxes_for_interval(video, start, end, detector_key)`，缺帧显式返回缺失标记。判据：接口有测试，缺检测帧不会被悄悄补成整帧。

## 2. 目录组织与代码归属（先定位置，再继续）

现状：可复用逻辑分布在 `scripts/` 与 `petlib/` 之间，边界靠习惯。约定（本次确定）：**`petlib/` 放可导入、可测试、无命令行的能力；`scripts/` 只做参数解析与编排**。

目标布局（待用户审定）：

| 当前文件 | 目标位置 | 说明 |
|---|---|---|
| `scripts/prepare_cat_crop_experiment.py` 的检测编排 | `petlib/detection/anchors.py`、`cache.py`、`fingerprint.py` | 抽样、缓存读写与复用校验、指纹 |
| 同文件的渲染编排 | `petlib/render/frames.py` | 逐帧方形裁剪 + 编码 |
| `scripts/build_cat_dataset_slices.py` 的筛选与切片 | `petlib/datasets/cat_selection.py` | 资格判定、重叠仲裁、外延、切片 |
| `scripts/build_clip_boxes.py` | `petlib/datasets/clip_boxes.py` | 轨迹 → 逐帧框 |
| `scripts/render_clip_windows.py` | `petlib/render/clips.py` | 片段渲染 |
| `scripts/export_clip_annotations.py` | `petlib/datasets/annotation_export.py` | 标注导出与帧数 clamp |
| `scripts/infer_single_clip.py` | `petlib/inference/recognizer.py` | 单片段推理封装 |
| `petlib/datasets/cat_intervals.py` 的 `CatIntervalMetric` | `petlib/metrics/cat_interval.py` | 指标与数据集解耦 |
| `scripts/pet_detect_track.py`、`pet_multi_detect.py`、`pet_batch_run.py` | `scripts/legacy/` | 旧管线入口，保留只读，不再演进 |
| 以上脚本本体 | 保留在 `scripts/`，只留 argparse 与调用 | 入口不变，行为不变 |

- [ ] 2.1 盘点现状：列出链路相关脚本与 petlib 模块，标注每个文件的职责与“是否含可复用逻辑”。判据：清单写入 evidence，覆盖本 change 涉及的全部文件。
- [ ] 2.2 把目标布局写进 design 与 `pet-pipeline` skill（含判断标准：能被两个以上入口复用、能脱离命令行被测试）。判据：design 与 skill 两处一致。
- [ ] 2.3 用户审定布局方案。判据：裁定结果写入 evidence；未审定前不搬代码。（依赖 2.2）
- [ ] 2.4 迁移检测编排到 `petlib/detection/`（anchors、cache、fingerprint，指纹按 mtime 缓存）。判据：脚本调用新模块，1 段视频的检测产物与迁移前哈希一致。（依赖 2.3）
- [ ] 2.5 迁移筛选与切片规则到 `petlib/datasets/cat_selection.py`。判据：`slices_v8` 重跑结果与现有 `clips.jsonl` 哈希一致。（依赖 2.4）
- [ ] 2.6 迁移逐帧框与片段渲染到 `petlib/datasets/clip_boxes.py`、`petlib/render/clips.py`。判据：单个片段的框序列与渲染产物哈希一致。（依赖 2.5）
- [ ] 2.7 迁移标注导出与单片段推理到 `petlib/datasets/annotation_export.py`、`petlib/inference/recognizer.py`。判据：导出的 ann 文件与现有 `datasets/cat_clip_v9/*.jsonl` 逐行一致；推理输出概率一致。（依赖 2.6）
- [ ] 2.8 旧脚本归入 `scripts/legacy/` 并标注只读。判据：`scripts/` 顶层不再出现这些文件，归档说明写入 evidence。（可与 2.7 并行）
- [ ] 2.9 更新 `pet-pipeline` skill 的代码地图与目录约定，使其与新布局一致。判据：skill 中每个路径都存在。（依赖 2.7、2.8）

## 3. 资格与筛选

- [x] 3.1 多宠物判定：以锚点（`frame % stride == 0`）为基准，覆盖率 ≥0.5 且连续 ≥3 判为多宠物。证据：`archive/2026-11-07-cat-data-preprocessing/evidence.md`。
- [x] 3.2 计数前规整检测：`distinct_pets` 丢弃与主框 IoU ≥ 0.8 的重复框、面积比 <0.15 或 >3 的退化框；多宠物 967 → 482。证据：同上。
- [x] 3.3 排除短于 1 秒的区间：33 条标 `too_short_annotation`。证据：`slices_v8/intervals.jsonl`。
- [x] 3.4 短区间左右外延：607 条 1–4 秒区间用真实相邻帧外延到 60 帧，不越邻区间与视频边界；失败 143 条记录原因。证据：同上。
- [x] 3.5 split 分配：沿用既有 day map，未匹配日期的 12 条记 `unassigned_split` 并排除。证据：同上。
- [x] 3.6 重叠仲裁：按“具体动作 > activity > prolonged_stationary”保留一条，被压制 22 条写 `suppressed_by`。证据：同上。
- [x] 3.7 多宠物登记：482 条写入 `pending_multi_pet.jsonl`，供按轨迹裁剪回收。证据：同上。

## 4. 切片与清单

- [x] 4.1 分层随机切片：区间按可容纳片段数切 k 段（k = min(4, 容量)），每段随机一个起点，seed=0，每区间 ≤4 片段。证据：`slices_v8/clips.jsonl`。
- [x] 4.2 activity 上限：封顶为第二大类的 3 倍（v8 中 3,784 vs 1,309，未触发削减）。证据：`slices_v8/summary.json`。
- [x] 4.3 片段清单字段：逐片段记录 `species`、`cat_count`、`dog_count`、`extended`、`shorter_than_clip`、`suppressed_by`，`sample_id` 唯一为“视频:起-止:类别”。证据：同上。
- [x] 4.4 损失逐条归因：`intervals.jsonl` 记录每个输入区间的去向与原因，原因计数之和等于 3,927。证据：同上。
- [x] 4.5 划分隔离核验：2,150 个视频的片段均落在单一 split，跨 split 视频 0 个。证据：同上。

## 5. 跟踪与逐帧框

- [x] 5.1 跟踪脚本改名与入口：`scripts/track_multi_pet.py` → `scripts/track_pet_targets.py`，对单、多目标都适用；单流 OC-SORT、物种作元数据。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 5.2 全量跑跟踪：2,335 个片段视频，60 秒完成，产物 `results/cat_clip_v9/tracks`。证据：同上。
- [x] 5.3 逐帧框生成：`scripts/build_clip_boxes.py` 取覆盖片段帧数最多的轨迹，线性插值到逐帧、端点保持、5 帧滑动平均；7,350 条片段有框，204 条无锚点被跳过。证据：同上。
- [x] 5.4 判定单位改为 (区间, 轨迹)：每条轨迹独立判断覆盖与缺口，一条被淘汰不影响其它；已作为 delta spec 合入 `cat-dataset-preprocessing`。证据：`openspec/specs/cat-dataset-preprocessing/spec.md`。

## 6. 渲染

- [x] 6.1 离线渲染片段：`scripts/render_clip_windows.py` 8 进程并行，7,350 条中 7,342 条成功，60 帧、256×256、crf 23，约 30 分钟、656 MB。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 6.2 渲染启动脚本：`scripts/remote/render_clip_windows.sh`，带资源守卫（CPU 900%、RSS 16 GB）。证据：同上。

## 7. 训练

- [x] 7.1 训练标注导出：`scripts/export_clip_annotations.py` 字符串标签 → 十类整数、补 `task_id`、按源视频帧数 clamp；片段模式下 `start/end` 固定 1/60。证据：同上。
- [x] 7.2 训练配置：`configs/cat_clipv9_videomaev2_b.py`，16 帧、间隔 3、256→224、十类、`accumulative_counts=4`（属 `optim_wrapper`）、`num_workers=6`、sqrt 逆频类别权重。证据：同上。
- [x] 7.3 训练执行：20 轮完成，rc=0、3,322 秒，best 为 `best_macro_f1_epoch_8.pth`（验证 top-1 83.82%、macro-F1 52.22%）。证据：报告 `cat-clip-training/20261107-clipv9-b`。

## 8. 评测与口径

- [x] 8.1 冻结测试：1,130 条片段只跑一次，top-1 85.75%、macro-F1 56.23%、balanced 54.62%。证据：同上。
- [x] 8.2 逐类与排除稀有类重算：排除 gnawing/fall/seizure 后 top-1 86.06%、macro recall 78.03%、漏检 13.94%；低召回集中在 scratching 56.4%、drinking 68.3%。证据：同上。
- [x] 8.3 准确率口径裁定：中期目标 75% 按留出子集条件准确率判定（已达成），端到端 72.9% 降为诊断量。证据：`AGENTS.md`。
- [x] 8.4 报告发布：`management/experiments/cat-clip-training/20261107-clipv9-b/`，12 段视频案例，完整度 0 项缺失。证据：报告目录。

## 9. 工具与文档

- [x] 9.1 单片段推理脚本：`scripts/infer_single_clip.py`，直接走 backbone → cls_head 并输出 softmax 概率。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 9.2 链路 skill：`.claude/skills/pet-pipeline/SKILL.md`，记录五段链路、代码地图、开工前检查表与已知限制。
- [x] 9.3 报告页版式与案例交互：侧栏 + 正文 + 章节目录；交替模式支持点击切换；案例改视频。证据：`archive/2026-11-07-web-experiments-report-layout/`、`web-experiment-case-picker/evidence.md`。

## 10. 采样间隔对齐（先量化再决定）

- [ ] 10.1 统计采样帧与检测锚点的重合率：对 7,342 条片段，计算 16 个采样帧（间隔 3）中有几帧落在锚点（每 5 帧）上。判据：逐片段重合帧数分布与总体重合率写入 evidence。（可与 10.2 并行）
- [ ] 10.2 统计插值框的位置误差：对不重合的采样帧，比较插值框与最近锚点框的四边位移。判据：位移中位数与 p90（像素）写入 evidence。（可与 10.1 并行）
- [ ] 10.3 依 10.1/10.2 结果裁定对齐方案：A（片段 80 帧 + 间隔 5）或 B（检测加密到 3）或 C（维持现状）。判据：用户裁定的方案与理由写入 evidence。（依赖 10.1、10.2）

## 11. activity 边界核查

- [ ] 11.1 随机抽 20 条 activity 片段并导出视频（含类别与判读信息）。判据：清单与文件路径写入 evidence。（可与 10.1 并行）
- [ ] 11.2 用户逐段判定：明显走动 / 无具体动作但不静止 / 应为其它类。判据：20 条判定表写入 evidence。（依赖 11.1）
- [ ] 11.3 依 11.2 裁定是否拆分 activity（或降级为并列属性）。判据：裁定与理由写入 evidence。（依赖 11.2）

## 12. 间隔对齐实施（按 10.3 选定方案）

- [ ] 12.1 按选定方案重做片段窗口（A：80 帧；B：先重检测再重切片）。判据：新片段数与帧数写入 evidence。（依赖 10.3）
- [ ] 12.2 重渲染片段并做媒体审计（帧数、尺寸、体积）。判据：审计通过，失败清单写明原因。（依赖 12.1）
- [ ] 12.3 用对齐后的输入重训 20 轮。判据：状态完成、best 检查点按 macro-F1 选出、四类产物齐备。（依赖 12.2）
- [ ] 12.4 与当前基线（top-1 85.75 / macro-F1 56.23 / macro recall 78.03）对照。判据：对照表写入 evidence 与报告。（依赖 12.3）

## 13. 输入信息增量

- [ ] 13.1 分辨率实验：256 → 384 重渲染，与 256 逐条对照体积与审计结果。判据：体积、渲染耗时、审计结论写入 evidence。（依赖 12.4）
- [ ] 13.2 用 384 重训并对照。判据：对照表写入 evidence。（依赖 13.1）
- [ ] 13.3 双通道实现：RGB + 帧差作为第二通道，先在 20 条片段上冒烟确认形状与可视化。判据：输出的张量形状与两张可视化图写入 evidence。（可与 13.1 并行）
- [ ] 13.4 双通道重训并对照（若 13.3 通过）。判据：对照表写入 evidence；失败也记录。（依赖 13.3、13.2）

## 14. 决策侧调整（最便宜，可并行）

- [ ] 14.1 阈值扫描：只改推理阈值与类别权重，扫 5 档，记录 scratching/drinking 召回与 activity 误报的取舍。判据：召回-precision 表写入 evidence。（可与 12.3、13.2 并行）
- [ ] 14.2 选定阈值并冻结：给出选定值与理由，说明对整体 top-1 的影响。判据：选定值写入 evidence 与报告。（依赖 14.1）

## 15. 多宠物片段纳入

- [ ] 15.1 为 328 对重叠区间（148 个视频）生成审阅页：并排两段轨迹片段 + 该时段的两个标签。判据：页面可用，条目数 328。（可与 14.1 并行）
- [ ] 15.2 用户完成标签归属标注。判据：标注文件落盘，覆盖率写入 evidence。（依赖 15.1）
- [ ] 15.3 按 (区间, 轨迹) 独立切片并合流到新索引版本。判据：新增片段数、按类计数写入 evidence。（依赖 15.2）
- [ ] 15.4 含多宠物片段重训并对照，同时报告 `subject_ambiguous` 占比。判据：对照表与占比写入 evidence。（依赖 15.3）
