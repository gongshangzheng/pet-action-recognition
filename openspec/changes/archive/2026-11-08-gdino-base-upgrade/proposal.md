> **Superseded by `pet-pipeline`。** 用户已批准合并并归档；本 change 原任务及 delta 保留，不将未实施规格同步主 spec。原 11 条全部未完成；没有补勾，也不代表教师小批或全量检测完成。 三份来源共 99 条逐号承接、原 checkbox 和证据边界见 [`pet-pipeline/task-map.md`](../../pet-pipeline/task-map.md)。归档不表示原 change 全部完成。

## Why

当前检测链路的教师是 GroundingDINO-tiny（约 172M），已实证存在四类系统性失败：把狗粮袋面印刷的金毛判为活狗（且稳定存在、置信 0.54）、同一只猫产出紧框+松框嵌套重复（IoS≈1.0）、物种标签抖动（同一只猫部分锚点被判 dog）、真猫漏检（覆盖率仅 54%）。这些失败被蒸馏进了 YOLO 学生（`gdino-distill-yolo-detector`，一致率 mAP@0.5=0.809 是循环验证）。

用户决定：换用 `grounding-dino-base`（约 860M）作教师，把整个检测→伪标签→蒸馏流程重跑一遍，并在动手全量重跑之前先用已人工核对过的段验证 base 是否真的更好。

## What Changes

- **下载与接入 gdino-base**：权重放 pet（清代理直连），复用现有检测入口（`petlib/detection/grounding_dino.py`），不改 prompt 与阈值（首轮只 cat/dog）。
- **对照实验（小批，先于全量）**：在已人工核对的 3 段（charw1g 狗粮袋 / 033836 夜间 / 0618 双猫）上，base vs tiny 逐锚点对照——核心问题：印刷金毛还检不检、物种抖动还有没有、嵌套重复变多还是变少、真猫漏检是否改善、速度代价多大。
- **实验报告**：对照结论落 `management/experiments/`，base 是否值得全量重跑由报告裁决（判据事先写定，见 design）。
- **全量重跑（仅当对照达标）**：2,737 段、全视频、stride=5（与现有缓存同口径；区间外帧保留，是负样本与进出画面过渡的来源）。产物写独立目录，不覆盖 tiny 缓存。
- **新伪标签数据集 + 重训 YOLO**：教师指纹变化触发重建数据集（每视频帧数上限提高，目标 ≥4 万框）；YOLO11s@1280 训 30–40 epochs（吸取上轮内存守卫教训，workers=2）。
- **三方对照**：YOLO(base 教师) vs YOLO(tiny 教师) vs tiny 教师本人，速度与一致率同报。

## Capabilities

### New Capabilities

- `gdino-base-upgrade`: 教师模型升级的验证闸门（小批对照先行、判据事先写定）、全量重跑的口径冻结（全视频/stride=5/独立目录）、以及新教师→新数据集→新学生的可追溯链。

### Modified Capabilities

无。`gdino-distill-yolo-detector` 的产物与结论保留不动，本 change 产出的新数据集与新学生与其并列对照。

## Impact

- GPU 成本：对照小批约 10–20 分钟；全量重跑约 13–17 小时（需分段守卫执行，占用 GPU0 长窗口，须与共享机协调）；YOLO 重训约 2–3 小时。
- 磁盘：base 权重约 690MB；新缓存约 200MB+；新数据集（提帧后）约 6GB。
- 下游影响：base 缓存是**新增**不替换；`multi-pet-sort-tracking`、`cat-data-preprocessing` 的既有结论基于 tiny 缓存，不受影响，但未来可选用 base 缓存重算。
- 环境不动：plf 主环境不加新依赖（base 权重走 transformers 既有 API，仅换 checkpoint 路径）。
