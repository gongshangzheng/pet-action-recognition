## 1. 已完成的实现细节

本节把此前五个 change 里已经落地的工作拆成单条，每条写清实现与证据；全部为已执行。

### 1.1 检测

- [x] 1.1.1 补检测缺失视频：`scripts/remote/run_missing_detection.sh` 对 429 段未检测视频跑 GroundingDINO，覆盖达 2,573 段，耗时 4,532 秒、rc=0。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.1.2 修复视频列表校验：`--video-list` 曾要求视频必须存在于源索引，导致被重叠过滤掉的 429 段无法补检；改为允许显式列表包含索引外视频。证据：同上。
- [x] 1.1.3 记录检测指纹：权重 SHA-256 `1a2412ef…`、box/text 阈值 0.3、`sample_stride=5`、`max_gap=10` 写入 evidence。证据：`archive/2026-11-07-cat-data-preprocessing/evidence.md`。

### 1.2 资格与筛选

- [x] 1.2.1 多宠物判定：以锚点（`frame % stride == 0`）为基准，覆盖率 ≥0.5 且连续 ≥3 判为多宠物；早期按 `source=="detected"` 过滤会把多宠物锚点（被写作 `invalid`）统计成 0，已修正。证据：同上。
- [x] 1.2.2 计数前规整检测：`distinct_pets` 丢弃与主框 IoU ≥ 0.8 的重复框、面积比 <0.15 或 >3 的退化框；多宠物 967 → 482。证据：同上。
- [x] 1.2.3 排除短于 1 秒的区间：33 条标 `too_short_annotation`。证据：`slices_v8/intervals.jsonl`。
- [x] 1.2.4 短区间左右外延：607 条 1–4 秒区间用真实相邻帧外延到 60 帧，不越邻区间与视频边界；失败 143 条记录原因。证据：同上。
- [x] 1.2.5 split 分配：沿用既有 day map，未匹配日期的 12 条记 `unassigned_split` 并排除。证据：同上。
- [x] 1.2.6 重叠仲裁：按“具体动作 > activity > prolonged_stationary”保留一条，被压制 22 条写 `suppressed_by`。证据：同上。
- [x] 1.2.7 多宠物登记：482 条写入 `pending_multi_pet.jsonl`，供按轨迹裁剪回收。证据：同上。

### 1.3 切片与清单

- [x] 1.3.1 分层随机切片：区间按可容纳片段数切 k 段（k = min(4, 容量)），每段随机一个起点，seed=0，每区间 ≤4 片段。证据：`slices_v8/clips.jsonl`。
- [x] 1.3.2 activity 上限：封顶为第二大类的 3 倍（v8 中 3,784 vs 1,309，未触发削减）。证据：`slices_v8/summary.json`。
- [x] 1.3.3 片段清单字段：逐片段记录 `species`、`cat_count`、`dog_count`、`extended`、`shorter_than_clip`、`suppressed_by`，`sample_id` 唯一为“视频:起-止:类别”。证据：同上。
- [x] 1.3.4 损失逐条归因：`intervals.jsonl` 记录每个输入区间的去向与原因，原因计数之和等于 3,927。证据：同上。
- [x] 1.3.5 划分隔离核验：2,150 个视频的片段均落在单一 split，跨 split 视频 0 个。证据：同上。

### 1.4 跟踪与逐帧框

- [x] 1.4.1 跟踪脚本改名与入口：`scripts/track_multi_pet.py` → `scripts/track_pet_targets.py`，对单、多目标都适用；单流 OC-SORT、物种作元数据。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.4.2 全量跑跟踪：2,335 个片段视频，60 秒完成，产物 `results/cat_clip_v9/tracks`。证据：同上。
- [x] 1.4.3 逐帧框生成：`scripts/build_clip_boxes.py` 取覆盖片段帧数最多的轨迹，线性插值到逐帧、端点保持、5 帧滑动平均；7,350 条片段有框，204 条无锚点被跳过。证据：同上。
- [x] 1.4.4 判定单位改为 (区间, 轨迹)：每条轨迹独立判断覆盖与缺口，一条被淘汰不影响其它；该要求已作为 delta spec 合入 `cat-dataset-preprocessing`。证据：`openspec/specs/cat-dataset-preprocessing/spec.md`。

### 1.5 渲染

- [x] 1.5.1 离线渲染片段：`scripts/render_clip_windows.py` 8 进程并行，7,350 条中 7,342 条成功（8 条源视频帧数不足），60 帧、256×256、crf 23，约 30 分钟、656 MB。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.5.2 渲染启动脚本：`scripts/remote/render_clip_windows.sh`，带资源守卫（CPU 900%、RSS 16 GB）。证据：同上。

### 1.6 训练

- [x] 1.6.1 训练标注导出：`scripts/export_clip_annotations.py` 字符串标签 → 十类整数、补 `task_id`、按源视频帧数 clamp；片段模式下 `start/end` 固定 1/60。证据：同上。
- [x] 1.6.2 训练配置：`configs/cat_clipv9_videomaev2_b.py`，16 帧、间隔 3、256→224、十类、`accumulative_counts=4`（属 `optim_wrapper`，此前误放进 `train_cfg`）、`num_workers=6`、sqrt 逆频类别权重。证据：同上。
- [x] 1.6.3 训练执行：20 轮完成，rc=0、3,322 秒，best 为 `best_macro_f1_epoch_8.pth`（验证 top-1 83.82%、macro-F1 52.22%）；读片段文件后 0.135 秒/迭代。证据：报告 `cat-clip-training/20261107-clipv9-b`。

### 1.7 评测与口径

- [x] 1.7.1 冻结测试：1,130 条片段只跑一次，top-1 85.75%、macro-F1 56.23%、balanced 54.62%。证据：同上。
- [x] 1.7.2 逐类与排除稀有类重算：排除 gnawing/fall/seizure 后 top-1 86.06%、macro recall 78.03%、漏检 13.94%；低召回集中在 scratching 56.4% 与 drinking 68.3%。证据：同上。
- [x] 1.7.3 准确率口径裁定：中期目标 75% 按留出子集条件准确率判定（已达成），端到端 72.9% 降为诊断量。证据：`AGENTS.md` 与 `archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.7.4 报告发布：`management/experiments/cat-clip-training/20261107-clipv9-b/`，`status=partial`、`verdict=improved`，12 段视频案例，完整度 0 项缺失。证据：报告目录。

### 1.8 工具与文档

- [x] 1.8.1 单片段推理脚本：`scripts/infer_single_clip.py`，直接走 backbone → cls_head 并输出 softmax 概率（此前把 logits 当概率、dtype 不匹配、维度错误均已修）。证据：`archive/2026-11-08-clip-box-crop-input/evidence.md`。
- [x] 1.8.2 链路 skill：`.claude/skills/cat-pipeline/SKILL.md`，记录五段链路、代码地图、开工前检查表与已知限制。证据：该文件。
- [x] 1.8.3 报告页版式与案例交互：文档页式侧栏 + 正文 + 章节目录，交替模式支持点击切换与前后按钮，案例改视频。证据：`archive/2026-11-07-web-experiments-report-layout/` 与 `web-experiment-case-picker/evidence.md`。

## 2. 采样间隔对齐（先量化再决定）

- [ ] 2.1 统计采样帧与检测锚点的重合率：对 7,342 条片段，计算 16 个采样帧（间隔 3）中有几帧落在锚点（每 5 帧）上。判据：逐片段重合帧数分布与总体重合率写入 evidence。（可与 2.2 并行）
- [ ] 2.2 统计插值框的位置误差：对不重合的采样帧，比较插值框与最近锚点框的四边位移。判据：位移中位数与 p90（像素）写入 evidence。（可与 2.1 并行）
- [ ] 2.3 依 2.1/2.2 结果裁定对齐方案：A（片段 80 帧 + 间隔 5）或 B（检测加密到 3）或 C（维持现状）。判据：用户裁定的方案与理由写入 evidence。（依赖 2.1、2.2）

## 3. activity 边界核查

- [ ] 3.1 随机抽 20 条 activity 片段并导出视频（含类别与判读信息）。判据：清单与文件路径写入 evidence。（可与 2.1 并行）
- [ ] 3.2 用户逐段判定：明显走动 / 无具体动作但不静止 / 应为其它类。判据：20 条判定表写入 evidence。（依赖 3.1）
- [ ] 3.3 依 3.2 裁定是否拆分 activity（或降级为并列属性）。判据：裁定与理由写入 evidence。（依赖 3.2）

## 4. 间隔对齐实施（按 2.3 选定方案）

- [ ] 4.1 按选定方案重做片段窗口（A：80 帧；B：先重检测再重切片）。判据：新片段数与帧数写入 evidence。（依赖 2.3）
- [ ] 4.2 重渲染片段并做媒体审计（帧数、尺寸、体积）。判据：审计通过，失败清单写明原因。（依赖 4.1）
- [ ] 4.3 用对齐后的输入重训 20 轮。判据：状态完成、best 检查点按 macro-F1 选出、四类产物齐备。（依赖 4.2）
- [ ] 4.4 与当前基线（top-1 85.75 / macro-F1 56.23 / macro recall 78.03）对照。判据：对照表写入 evidence 与报告。（依赖 4.3）

## 5. 输入信息增量

- [ ] 5.1 分辨率实验：256 → 384 重渲染，与 256 逐条对照体积与审计结果。判据：体积、渲染耗时、审计结论写入 evidence。（依赖 4.4）
- [ ] 5.2 用 384 重训并对照。判据：对照表写入 evidence。（依赖 5.1）
- [ ] 5.3 双通道实现：RGB + 帧差作为第二通道，先在 20 条片段上冒烟确认形状与可视化。判据：输出的张量形状与两张可视化图写入 evidence。（可与 5.1 并行）
- [ ] 5.4 双通道重训并对照（若 5.3 通过）。判据：对照表写入 evidence；失败也记录。（依赖 5.3、5.2）

## 6. 决策侧调整（最便宜，可并行）

- [ ] 6.1 阈值扫描：只改推理阈值与类别权重，扫 5 档，记录 scratching/drinking 召回与 activity 误报的取舍。判据：召回-precision 表写入 evidence。（可与 4.3、5.2 并行）
- [ ] 6.2 选定阈值并冻结：给出选定值与理由，说明对整体 top-1 的影响。判据：选定值写入 evidence 与报告。（依赖 6.1）

## 7. 多宠物片段纳入

- [ ] 7.1 为 328 对重叠区间（148 个视频）生成审阅页：并排两段轨迹片段 + 该时段的两个标签。判据：页面可用，条目数 328。（可与 6.1 并行）
- [ ] 7.2 用户完成标签归属标注。判据：标注文件落盘，覆盖率写入 evidence。（依赖 7.1）
- [ ] 7.3 按 (区间, 轨迹) 独立切片并合流到新索引版本。判据：新增片段数、按类计数写入 evidence。（依赖 7.2）
- [ ] 7.4 含多宠物片段重训并对照，同时报告 `subject_ambiguous` 占比。判据：对照表与占比写入 evidence。（依赖 7.3）
