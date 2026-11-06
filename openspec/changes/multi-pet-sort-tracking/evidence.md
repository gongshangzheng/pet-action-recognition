# 实验证据

### 2026-11-07：1.1 锚点序列读取（判据：3 段视频锚点数一致）

- 实现 `petlib/tracking/anchors.py`（commit `1dbf043`）：读 cat-crop-detection-v2 缓存，还原逐锚点 `cat_candidates`/`dog_candidates`，锚点帧序列校验内建（不符即抛错）。
- 判据验证：3 段真实缓存（0_chi2m65__event_20260410_235950 / 0413_090514 / 0419_073622），锚点数 46/76/49，均等于 `frame % 5 == 0` 应得帧数；首锚点候选还原正确（狗×2 / 猫×2 / 空）。

### 2026-11-07：1.2 OC-SORT 接入与合成用例（判据：平行保 id、交叉不换 id）

- 实现 `petlib/tracking/oc_sort.py` 生命周期参数透传（max_age/min_hits/iou_threshold/det_thresh，design 4.7 锚点数标定：max_age=8≈2.7s、min_hits=2）与 `petlib/tracking/species_split.py`（猫/狗分实例，dog id 偏移 +10000）。commit `e36574c`。
- 依赖：boxmot 25.0.0（`--no-deps` 安装，与 pet 上 plf 环境同版本）+ lap + loguru。
- 判据验证（真实 OcSort 实例，非 mock）：A 平行——两狗匀速右移 20 锚点，2 条长轨迹 id 稳定；B 交叉——左起点轨迹 150→1195、右起点 850→-195，穿越交叉未互换；C 物种——猫狗框重叠 10 锚点，cat id=0 / dog id=10000 无串扰。

### 2026-11-07：1.3 产物与可复现（判据：同输入同参数哈希一致）

- 实现 `scripts/track_multi_pet.py`（commit `e1966d6`），输出独立目录：逐视频 `<stem>.track.json`（逐锚点 track id/框/物种/状态 + 检测指纹 + 参数）+ `manifest.json`（检测 sha256、内容哈希）。
- 判据验证：3 段重跑，内容哈希逐字节一致（`9d51b353…` 两轮相同）。

### 2026-11-07：2.1 评估集选取（判据：清单含视频名、区间、种子）

- 数据搬运：检测缓存全量 2,573 份（140MB，含 11-07 补检测批次 429 份）与区间表（sha256 `80da23af…` 与历史记录一致）取回本地 `results/tracking_eval_20261107/`。
- 实现 `scripts/select_multi_pet_eval.py`（commit `d60d2dc`），判据口径逐字复用 `build_cat_dataset_slices.py`（锚点=frame%stride==0、pet_count≥2、LABEL_MAP/DROP 一致）。
- **口径差异披露**：全量缓存下稳定多宠物区间 968 个（按视频去重 643 段），种子 20261107 抽 10 段。evidence（cat-data-preprocessing）记录的 565 基于 2026-11-07 早期的 2,144 段集合；同集合在 pet 上复算得 571（差 6，1.1%，原因未定位；两次已知历史统计错误不在此列）。选样用全量缓存，规则与种子固定，可复现。

### 2026-11-07：2.2 OC-SORT 三指标（判据：metrics 含三指标与逐视频明细）

- 实现 `scripts/eval_multi_pet_tracking.py`（commit `e6eac8e`）。无 GT 条件下的代理：碎片=同物种 confirmed 轨迹按时间近邻（gap≤24 锚点）聚类的段数-1；交换=同物种轨迹对共享帧 IoU>0.5 次数（必要非充分信号，真值靠 2.4 人工）；一致性=多宠物锚点上活跃轨迹数==pet_count 的占比。
- 结果（`metrics_ocsort_v1.json`）：碎片/个体最大 4（阈值 ≤2，**超标**）；交换信号 0；锚点一致性中位 0.82、最小 0.56。
- 不一致全是 under（轨迹数 < pet_count）：两段 charw1g 视频的 pet_count 3-4 锚点，候选框两两 IoU≈0（非近重复），是置信度 ≈0.3 的瞬态检出构不成轨迹——**pet_count 本身有噪声**，2.4 人工核对需仲裁画面真实个体数。

### 2026-11-07：2.3 原版 SORT 对照（判据：对照表含三指标与差异说明）

- boxmot 25.0.0 无独立 SORT；对照用同实现开关式（`--inertia 0 --no-use-byte`，Kalman/生命周期/匈牙利完全相同，只关被研究机制），避免自研近似（tracker-selection 教训）。commit `68181d2`。
- **结论：逐帧等价**。10 段全部 0 帧级差异（track 结构、框、轨迹长度分布完全相同；manifest 内容哈希差异仅来自 params 字段）。机制解释：① 缓存检测最低置信度 0.30 = box_threshold，无低分池，use_byte 二次关联结构性不触发；② 方向代价归零后匈牙利在 IoU 相似度上的分配不变——该评估集的匹配歧义不足以让 OCM 改变任何一次分配。
- 含义：碎片化主因是漏检间隙（max_age 内无观测），不是关联错误；3.2 的"算法 vs 密度"问题初步答案偏向密度（待 2.4/2.5 人工核对轨迹正确性后定论）。
