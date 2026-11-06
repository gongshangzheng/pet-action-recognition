---
name: cat-pipeline
description: |
  猫/狗行为数据从头到训练的完整链路速查：源视频 → 检测缓存 → 裁剪渲染 → 片段索引 → 训练标注 → mmaction2 训练/评测，含每步的产物路径、命令、已知坑与开工前检查表。
  触发场景：(1) 要训练行为模型 (2) 要改数据预处理/切片/索引 (3) 不清楚某一步的产物在哪 (4) 怀疑输入不是裁剪画面 (5) 训练报错或数据对不上
---

# 猫行为数据 → 训练 完整链路

**先读这一条**：连续几天的工作里最容易忘的两件事是——
1. **训练到底读整帧还是裁剪画面**（当前默认读整帧，裁剪视频虽然存在但没接进索引）；
2. **哪一步的产物是“权威版本”**（`slices_v8` 与 `datasets/cat_clip_v8`，不要用 v3/v7 的数字）。

## 链路全景

```text
cat_raw/videos/*.mp4  (原始事件视频 2880×1620, 15fps)
   │
   ├─ ①检测  prepare_cat_crop_experiment.py --stage detect
   │        → assets/full_run/detections/<stem>.json
   │          anchors: 每 sample_stride(=5) 帧一个，含 cat_count/dog_count/candidates(box+score)
   │          指纹: fingerprint.weights_sha256、box_threshold 0.3、text_threshold 0.3
   │
   ├─ ②渲染  prepare_cat_crop_experiment.py --stage render
   │        → assets/full_run/videos/gdino/<stem>.mp4      (B 臂，512×512，无文字)
   │        → assets/full_run/videos/gdino_motion/<stem>.mp4 (C 臂)
   │        → assets/full_run/metadata/<stem>.json         (逐帧 camera_box/display_box/valid)
   │
   ├─ ②b 跟踪  scripts/track_multi_pet.py  (OC-SORT，单流，物种作元数据)
   │        → <out>/<stem>.track.json  逐锚点轨迹（含输入指纹与参数）
   │        规则见 petlib/tracking/：IoS≥0.8 去嵌套重复、生命周期标定、放弃不稳定轨迹
   │
   ├─ ③切片  scripts/build_cat_dataset_slices.py
   │        → results/cat_data_preprocessing/slices_v8/clips.jsonl    (7,554 条片段)
   │        → .../index/{train,val,test}.jsonl  .../intervals.jsonl  .../summary.json
   │        → .../pending_multi_pet.jsonl (482 条待跟踪裁剪)
   │
   ├─ ④导出  scripts/export_clip_annotations.py
   │        → datasets/cat_clip_v8/{train,val,test}.jsonl  (整数 label + start_frame/end_frame/task_id)
   │
   └─ ⑤训练  models/mmaction2/tools/train.py configs/cat_clip_videomaev2_b.py
            → results/cat_clip_v8/train20/{work,log,metrics}
```

## 各步骤的权威产物与命令

### ① 检测（GPU，约 7 秒/段）

```bash
python3 scripts/prepare_cat_crop_experiment.py --stage detect \
  --index-root ~/pet-final/datasets/cat_action_v1 \
  --video-root ~/pet-final/datasets/cat_raw \
  --asset-root results/cat_crop_classification/gdino-crop-20261103a/assets/full_run \
  --dataset-root datasets/cat_crop_classification/gdino-v1-full \
  --video-list tmp/<list>.txt --sample-stride 5 --max-gap 10 --device cuda:0
```
- 缓存 schema `cat-crop-detection-v2`，**多宠物锚点会被写成 `source=invalid`**：统计多宠物时必须读 `anchors` 原始计数，不能按 `source=="detected"` 过滤（这个坑踩过两次）。
- `decoded_frames` 可能大于播放器实际帧数 → 导片段时要 clamp。

### ② 渲染（CPU，约 24 秒/段）

- 输出 B/C 两路 mp4，512×512，**已经存在 2,144 段**；补检测新增的 314 段尚未渲染。
- B 臂用 `display_box`（最高置信度宠物框），**不是标注所指的那只**；单宠物片段没问题，多宠物片段可能裁到狗。

### ③ 切片（CPU，5 秒全域）

```bash
python3 scripts/build_cat_dataset_slices.py --intervals .../intervals.csv \
  --detection-dir .../detections --split-manifest .../cat_action_v1/split_manifest.json \
  --out results/cat_data_preprocessing/slices_v8
```
顺序：剔非闭集类别 → 剔短于 1 秒 → 多宠物判定（先去重复框 IoU≥0.8、退化框面积比 0.15–3）→ 按日分 split → 重叠仲裁（具体动作 > activity > prolonged_stationary）→ 短区间左右外延到 60 帧 → 分层随机切片（≤4/区间，seed=0）→ activity ≤ 3×第二大类。

**坑**：`sample_id` 必须唯一（`视频:起-止:类别`）。曾用 `annotation_id`，同任务多行共用，导致每区间片段数错乱与邻区间边界互相覆盖。

### ④ 导出训练标注

```bash
python3 scripts/export_clip_annotations.py --clips .../slices_v8/clips.jsonl \
  --out datasets/cat_clip_v8 --video-root /home/wyy/pet-final/datasets/cat_raw
```
- 字符串 label → 十类整数；`start/end` → `start_frame/end_frame`；补 `task_id`；**逐视频探测帧数并 clamp**（否则 `Interval [1119,1178] exceeds 1031 frames`）。

### ⑤ 训练

```bash
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 PYTHONPATH=/home/wyy/pet-action-recognition \
python3 models/mmaction2/tools/train.py configs/cat_clip_videomaev2_b.py \
  --cfg-options work_dir=results/cat_clip_v8/train20
```
- 数据侧：`IntervalVideoDataset` + `RestrictFrameRange`（按帧号在区间内采样）+ `SampleFrames(16, interval 4)`。
- **当前输入是整帧**：索引 `video` 指向 `cat_raw/videos/*.mp4`。2880×1620 缩到短边 256 后猫只有十几像素。
- **裁剪输入的正确接法**：把索引 `video` 指向 `assets/full_run/videos/gdino/<stem>.mp4`（帧数/fps 一致，媒体审计已验），不需要新 transform。
- 实测吞吐：`num_workers=6` 时 0.47 s/迭代（1,127 迭代/轮 ≈ 11 分钟），20 轮 ≈ 4.4 小时；`num_workers=2` 会掉到 1.0 s/迭代。

## 代码地图（想改什么 → 改哪里）

| 想改的东西 | 文件 |
|---|---|
| 检测/渲染阶段、`--stage`、路径与指纹 | `scripts/prepare_cat_crop_experiment.py` |
| 方形裁剪、补边、逐帧轨迹与显示平滑 | `petlib/datasets/cat_crop.py`（`crop_square` 378、`build_frame_track` 133、`classify_frame`） |
| 跟踪算法、IoS 去重、生命周期、轨迹合并 | `petlib/tracking/`（`anchors.py` 的 `dedup_nested`、`oc_sort.py`、`merge.py`）、入口 `scripts/track_multi_pet.py` |
| 切片、损失归因、多宠物判定、activity 上限 | `scripts/build_cat_dataset_slices.py` |
| 训练标注导出、帧数 clamp | `scripts/export_clip_annotations.py` |
| 数据集读取、区间限制、评测指标 | `petlib/datasets/cat_intervals.py`（`IntervalVideoDataset`、`RestrictFrameRange`、`CatIntervalMetric`） |
| 逐帧裁剪 transform（未接入） | `petlib/datasets/cat_crop_transforms.py`（`SampledBoxCrop`/`BoxSquareCrop`） |
| 训练配置（十类、累加、权重） | `configs/cat_clip_videomaev2_b.py` 与 `configs/cat_action_videomaev2_b_v1.py` |
| 训练入口 / 产物解析 / checkpoint | `scripts/run_cat_crop_experiment.py`、`models/mmaction2/tools/train.py` |
| 远程启动与守卫 | `scripts/remote/run_missing_detection.sh`、`scripts/remote/run_clip_training.sh`、`.claude/skills/remote-ops/` |

## 裁剪输入：现状与已定方案

- **现状**：训练读整帧（索引 `video` 指向 `cat_raw/videos/*.mp4`）。整段渲染好的裁剪视频（`assets/full_run/videos/gdino*`，2,144 段）**不用于训练**，只保留审阅与对照——它用“最高置信度宠物框”，多宠物会裁到狗，也拿不到轨迹。
- **已定方案（change `clip-box-crop-input`）**：对片段视频跑跟踪 → 取覆盖片段帧数最多的轨迹 → 插值到逐帧、缺口沿用端点、5 帧滑动平均 → 框序列写入索引 `boxes` → 读训练样本时按 `frame_inds` 逐帧裁剪（补边不拉伸，无框回落整帧）。
- **不要**再另写一套“连续优先选框”规则：IoS 去重、单流关联、生命周期、放弃不稳定轨迹都已在 `multi-pet-sort-tracking` 定过并实测，直接复用。

## 开工前检查表（每次训练/改数据都过一遍）

1. 读的是整帧还是裁剪画面？在索引里看 `video` 指向哪个目录。
2. 索引是哪个版本？权威版本 `slices_v8` + `datasets/cat_clip_v8`；不要引用 v3/v7。
3. `num_classes` 与 `classes` 列表长度、`class_weight` 长度三者一致（基类残留七类是踩过的坑）。
4. `accumulative_counts` 属于 `optim_wrapper`，不属于 `train_cfg`。
5. 训练命令必须带 `PYTHONPATH=<repo>`，否则 `petlib` 导入失败。
6. 守卫上限：CPU 900%、RSS 24 GB、GPU 92%；时长按 20 轮 + 验证估。
6b. 裁剪是否真的生效？看索引里是否有 `boxes`、pipeline 里是否有裁剪 transform；两者缺一个就是整帧训练。
7. 跑完核对：`best_macro_f1_epoch_*.pth` 存在、checkpoint 含 `optimizer` 与 `param_schedulers`（基类默认 `save_optimizer=False`，改过才有效）。
8. 报数口径：端到端准确率 = 可用率 × 条件准确率（AGENTS.md 有定义），不要只报条件准确率。

## 已知限制（写结论时必须带上）

- 检测 3 Hz（stride 5）+ 远景小目标 → 漏检与重复框都多；多宠物判定受影响。
- `seizure` 0 片段、`fall` 1–2、`gnawing` 13–17：不能当结论。
- 片段只出清单，不导出 mp4；裁剪视频是“整段渲染”的现成产物（2,144 段）。
- `results/`、`datasets/` 都不入库，产物只在 pet；仓库里只有脚本与索引结构说明。
