## 1. 轨迹与片段产出

- [x] 【移交】1.1 从 `slices_v8/pending_multi_pet.jsonl` 取 482 个多宠物区间，对应视频去重后列出清单。判据：清单区间数 482、视频数写入 evidence。（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】1.2 对这些视频运行跟踪（复用 `scripts/track_pet_targets.py`），产出逐锚点轨迹。判据：轨迹文件覆盖全部清单视频，单视频失败如实记录。（依赖 1.1）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】1.3 按轨迹切片：60 帧窗、每条轨迹最多 4 个窗口、分层随机起点，片段继承区间标签与轨迹物种。**每条轨迹独立判定覆盖与缺口，不共用同一区间结论。**判据：抽样 10 条核对窗口落在区间内、轨迹仅属单一 track；多轨迹视频逐轨迹给出通过/淘汰明细。（依赖 1.2）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】1.4 片段清单补齐字段：`track_id`、`species`、`coverage`、`mean_conf`、`area_ratio`、`suspect_reasons`、`subject_ambiguous`。判据：清单里六个字段全部存在，抽样 1 条能读全。（依赖 1.3）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】1.5 抽样 20 条核对字段完整性与可追溯性（每条能回到来源区间与轨迹）。判据：20 条逐条结论写入 evidence。（依赖 1.4；可与 2.1 并行）（后续在 cat-pipeline-consolidation 执行）

## 2. 噪声量化

- [x] 【移交】2.1 人工抽检 20 条片段：判“可用（该物种活体）/不可用（印刷物、杂物、裁错）”，并记录不可用类型。判据：20 条结论与可用率写入 evidence。（可与 1.5 并行）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】2.2 统计 `suspect_reasons` 与人工判定的关系，给出可疑标记的灵敏度/特异度。判据：混淆表写入 evidence。（依赖 2.1）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】2.3 由用户依据 2.1/2.2 定可用率门槛与是否接入。判据：门槛值写入 evidence。（依赖 2.1、2.2）（后续在 cat-pipeline-consolidation 执行）

## 3. 合流与报告

- [x] 【移交】3.1 达门槛则合成 `datasets/cat_clip_v9`（v8 + 多宠物片段），划分沿用既有 day map。判据：新索引分片行数、跨 split 视频数写入 evidence。（依赖 2.3）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】3.2 报告扩量前后的可用率、类别分布、物种分布与 `subject_ambiguous` 占比。判据：四组数字写入报告。（依赖 3.1）（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】3.3 【条件】若 2.3 判定不达门槛：记录“多宠物轨迹仍不可用”及原因，跳过 3.1–3.2。判据：结论写入 evidence，且不生成 v9。（依赖 2.3；仅在不达门槛时执行）（后续在 cat-pipeline-consolidation 执行）
