## Why

十类片段集（`slices_v8`，7,554 片段、train 4,506 / val 1,871 / test 1,171）已经就绪，1 epoch 冒烟跑通，但还没有任何准确率数字。中期目标要求端到端准确率 ≥75%、漏检率 ≤10%，必须先有一轮完整训练与一次冻结测试。

## What Changes

- 用 `configs/cat_clip_videomaev2_b.py` 训练 VideoMAEv2-B 十类模型：20 epoch、micro-batch 4 + 累积 4、每 2 轮验证、sqrt 逆频类别权重。
- 训练完成后只做一次冻结测试，产出 top-1、macro-F1、balanced accuracy、逐类 recall/support，并给出按物种分组的指标。
- 报告按 AGENTS.md 的中期目标口径写：端到端准确率 = 可用率（3,339 / 3,927 = 85%）× 条件准确率；漏检率按区间级 `1 − recall` 报告，并说明事件级尚未测量。

## Capabilities

无新增或修改的能力：这是既有 `cat-action-training` 能力在新数据集上的一次运行，训练契约不变，故 `skip_specs: true`。

## Impact

- 新增配置与远程运行脚本；不改数据集、不改评测契约。
- GPU 占用约 12.4 GB 显存、CPU 约 800%（6 个解码 worker），预计 4.4 小时。
- 产物写入 `results/cat_clip_v8/`，不覆盖既有七类结果。
