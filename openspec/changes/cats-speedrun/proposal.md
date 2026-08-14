## Why

cats-dataset-v1 的 3 个模型（TSM / SlowOnly / TimeSformer）已训练完成，需要通过 speed run 测量推理速度、吞吐量和 GPU 显存占用，并与 UCF101 旧结果对比，评估模型的实时部署可行性。

## What Changes

- **Speed Run 评测**：对 3 个模型在 quadruped_cats_v1 test split 上做完整 speed run，输出标注视频 + RTF/显存指标
- **汇总报告**：整理 RTF、GPU 显存、推理时间，填入 cats-dataset-v1 的 tasks.md 结果表

## Capabilities

无新增 spec 级能力，纯评测执行。

## Impact

- `results/speedrun/results.json` 新增 quadruped_cats_v1 条目
- `openspec/changes/cats-dataset-v1/tasks.md` T4.1 更新 speed run 指标
