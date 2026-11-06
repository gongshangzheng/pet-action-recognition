## Why

当前 ten-class 训练读的是**整帧**：片段清单只记录视频与帧范围，检测框只用于判断区间可用性。整帧在 2880×1620 下缩到短边 256 后，猫只有十几个像素，既解释了检测漏检，也让分类上限受限。最初的目标是“用 GroundingDINO 裁剪后再训练”，因此需要把框真正用于输入。

## What Changes

- 片段索引增加 `crop_box`（每条片段一个固定框，取该片段内目标框的并集并加边距），多宠物片段取对应轨迹的框。
- 新增一个 mmaction2 transform，在 `Resize` 前按 `crop_box` 裁方形再缩放；视频仍读原始 mp4，不导出片段视频文件。
- 用同一批片段、同一配方跑两条臂：A 整帧（已有部分结果）、B 固定框裁剪，比较 top-1 与 macro-F1。
- 报告裁剪命中率（多少片段有可用框、多少回退整帧）与抽检案例。

## Capabilities

无新增能力：这是输入表示的一次实验改动（`skip_specs: true`）。

## Impact

- 修改 `scripts/build_cat_dataset_slices.py`（写 `crop_box`）、新增 transform 与新配置，不改 `slices_v8` 既有产物（新增字段写新版本 v9）。
- 需要一次裁剪臂训练（约 3–4 小时）与一次对照分析。
- 多宠物轨迹裁剪复用同一机制，但数据合流仍归 `multi-pet-track-cropping` change。
