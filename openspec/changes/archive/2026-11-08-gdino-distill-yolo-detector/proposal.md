> **Superseded by `pet-pipeline`。** 用户已批准合并并归档；本 change 原任务及 delta 保留，不将未实施规格同步主 spec。原 11 条中 5 条历史完成、6 条未完成；20/30 轮训练中止，未补勾。 三份来源共 99 条逐号承接、原 checkbox 和证据边界见 [`pet-pipeline/task-map.md`](../../pet-pipeline/task-map.md)。归档不表示原 change 全部完成。

## Why

GroundingDINO 是当前唯一的检测来源，但它慢：实测 stride=2 时 10 段视频（约 1,800 个锚点）耗时 **267 秒**（约 0.15 s/锚点），全量 2,144 段 stride=5 的历史批次耗时 **4 小时 17 分**。这个速度既无法支撑实时推理，也让离线重跑（换阈值、加密锚点、扩类目）成本高到不可接受。

同时我们已经有大量可用的教师输出：**2,573 段视频的 GroundingDINO 检测缓存**（`results/cat_crop_classification/gdino-crop-20261103a/assets/full_run/detections/`，含 11-07 补检测批次），每份含逐锚点的猫狗候选框、置信度与物种。

已有的反面证据说明"直接拿来用"不可行：COCO 预训练 YOLO11 在本域 zero-shot 体检中，**夜视红外条件下 cat 漏检率约 89%**（`openspec/changes/archive/2026-09-10-yolo11-detection-prep`）。所以必须用本域数据微调/蒸馏，而不是换一个现成权重。

本 change 要回答一个问题：**用 GroundingDINO 作教师蒸馏一个 YOLO 检测器，能否在保持可用检出质量的前提下，把推理速度降一个数量级以上。**

## What Changes

- **伪标签导出管线**：把现有 DINO 检测缓存转成 YOLO 训练格式，导出前必须过滤——嵌套重复框（IoS ≥ 0.8）、低置信候选、退化框；每帧记录丢弃数与原因，产物可追溯回源视频与教师指纹。
- **数据集划分**：按视频划分 train / val / test，同一源视频不得跨 split（否则伪标签泄漏会虚高指标）。
- **训练学生模型**：Ultralytics YOLOv8/YOLO11，只做 `cat` / `dog` 两类。（许可证 AGPL-3.0 作为已知约束记录在 design，数据管线与模型解耦，必要时可换 Apache-2.0 的 YOLOX。）
- **速度与一致率评测**：同硬件、同帧数对比学生与教师的端到端耗时；在留出视频上测学生与教师的一致率（mAP@0.5）。
- **明确不做**：不做人工框标注（后续另议）；不扩类目（人、家具、食盆等留到二期）；**不替换现有生产检测链路**（未获单独授权）。

## Capabilities

### New Capabilities

- `pet-detector-distillation`: 用 GroundingDINO 作教师导出伪标签、训练快模型、并同时报告速度与一致率的契约；明确一致率不等于真实准确率。

### Modified Capabilities

无。

## Impact

- 新增数据导出与训练脚本、YOLO 格式数据集目录、训练产物（checkpoint、指标、速度基准）。
- 需要 GPU 训练（pet，共享机，按 remote-ops 三道闸执行）。
- 新增外部依赖：`ultralytics`（AGPL-3.0）与其预训练权重；许可证影响面记录在 design。
- 不改动现有检测缓存、跟踪产物、动作识别索引与训练配方。
