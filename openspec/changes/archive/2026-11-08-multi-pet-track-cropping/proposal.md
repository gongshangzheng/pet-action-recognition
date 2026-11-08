## Why

数据集当前排除了 482 个“多宠物”区间（`pending_multi_pet_tracking`），它们占标注区间的 12%。跟踪工作已给出每条轨迹的框序列与质量信号，`multi-pet-sort-tracking` 的结论是“不适用于自动裁剪”，理由是存在稳定误检（例如袋面印刷的金毛被跟踪成 85% 覆盖的狗）。用户判断：**少量误检可以接受，大部分轨迹足以用于训练**，因此改为“按轨迹裁剪 + 量化噪声”，而不是全有或全无。

## What Changes

- 对 482 个多宠物区间所在视频运行跟踪，按轨迹裁出等长片段（沿用 60 帧、每区间每轨迹最多 4 片段的规则）。
- 片段清单增加 `track_id`、`species`、`coverage`、`mean_conf`、`area_ratio`、`suspect_reasons`、`subject_ambiguous` 字段；不因为可疑就删除，只记录。
- 人工抽检 20 条估计可用率；把结果作为接入依据，而不是逐条判定。
- 通过后并入数据集，产出新索引（不覆盖 `slices_v8`），报告新的可用率与类别/物种分布。

## Capabilities

无新增能力：这是在既有数据集与跟踪产物上的一次扩展，规则与清单契约不变（`skip_specs: true`）。

## Impact

- 复用 `scripts/track_pet_targets.py` 与 `scripts/build_cat_dataset_slices.py`，新增轨迹→片段步骤。
- 训练数据从 4,506 个训练片段增加若干百条（多宠物区间贡献的部分），噪声率需在报告中量化。
- 不改 `slices_v8` 与当前训练任务；新数据以新索引版本提供，待训练侧另行切换。
