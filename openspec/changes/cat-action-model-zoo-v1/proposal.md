# 猫动作训练 v1 参考模型批次

日期：2026-10-24，状态：实施任务已完成，待规格校验及归档（用户 2026-10-24 明确指示“可以下新的依赖到服务器上，开始下一批模型的训练吧”）。

## Why

`cat-action-training-v1` 只比较了 TSN R50 和 TSM R50（测试 macro-F1 57.5% / 61.8%）。用户想多训几个不同家族的模型作参考，以判断瓶颈在模型还是在数据（理毛、异常召回很低）。

## What Changes

在同一份 v1 七类索引、同一划分上，再训练 4 个模型，并与 TSM/TSN 一起只按验证集排名：

| 模型 | 采样 | 输入 | 预训练 |
|---|---|---|---|
| VideoMAEv2-B | 16 帧 × 间隔 4 | 224 | K710 蒸馏（`videomaev2-base`） |
| UniFormerV2-B | 8 帧均匀 | 224 | CLIP + K710（`uniformerv2-base`） |
| X3D-S | 13 帧 × 间隔 3 | 182 | K400（`x3d-xs` 目录，实为 X3D-S） |
| SlowFast R50 | 32 帧 × 间隔 2 | 224 | K400（`slowfast-resnet50`） |

- 不加帧缓存，直接读原视频（用户决定）。
- 不新装依赖：einops 0.8.2、timm 0.9.16、pytorchvideo 0.1.5、fvcore 已在 `.runtime/pet`。
- 结果写入 `results/training/cat_action_v1/<model>/`，不覆盖 TSM/TSN 和旧 smoke 结果。
- 验证集排名先冻结写入 `model_zoo_ranking.json`，再跑各模型 test。

## 与 TSM/TSN 基线的差异（报告必须注明）

- 新模型用 AMP 混合精度；基线是 fp32。
- VideoMAE/UniFormer 与基线均用 backbone `init_cfg`；X3D/SlowFast 用 `load_from` 加载整模权重（分类头形状不符的键被跳过）。预检验证 backbone 权重确实载入。
- 新模型随机裁剪面积范围 0.5–1.0，基线用 MultiScaleCrop。
- 各模型使用各自标准的采帧方式，时间跨度不同。
- ViT 类模型加 drop_path 0.1，未调参。

## Non-goals

- 不调超参、不做多随机种子；不做帧缓存、猫中心裁剪、事件级评测。
- 不修改 v1 的数据索引、类别、划分、旧配置和旧结果。

## 验收

- 4 个模型各完成训练、最佳 checkpoint 验证和（排名冻结后的）测试，`run_status.json` 为 `complete`。
- 预检证明权重载入、采样帧落在标注区间内、显存可容纳。
- `model_zoo_ranking.json` 仅按验证集排名；报告含全部 6 个模型的对比表。
