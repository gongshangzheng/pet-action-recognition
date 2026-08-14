## Why

cats 数据集（79 视频，最长 124s）需要切段后适配现有训练框架。现有 21 个模型族中只有 12 个成功完成训练，mvit-small、x3d-xs、uniformer-base 反复失败。我们需要：① 构建规范的数据集 pipeline；② 选取在现有数据上表现最好的模型用于 cats 实验。

## What Changes

- **新增数据集** `quadruped_cats_v1`：79 个原始视频 → 4s clip 切段，生成训练/val/test split
- **新增切段脚本** `scripts/slice_cats_clips.py`：uniform stride=2s 切段逻辑，生成 mmaction2 兼容的 ann file
- **新增 dataset class**：规范化 dataset 路径/类目/ann_file 格式，适配现有训练路由
- **训练 4 个精选模型**：基于现有结果选取 top performer + 快速模型 + 轻量模型

## Capabilities

### New Capabilities

- `datasets/quadruped-cats-v1`：cats 视频切段数据集，从 `datasets/cats/` 软链接触发，输出 4s clip 集合及 mmaction2 manifest

## Impact

- **新增数据集**：`datasets/quadruped_cats_v1/` 写入 NAS `/home/wyy/mnt/cats/`
- **训练路由**：需在 `server/config.py` 注册 `QUADRUPED_CATS_*` 配置项，`server/routers/training.py` 识别新 dataset
- **模型选择**：仅训练现有已通过 mmaction2 registry 的模型，不引入新模型族
