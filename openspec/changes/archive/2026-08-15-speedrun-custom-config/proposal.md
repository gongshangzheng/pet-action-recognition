# speedrun-custom-config Proposal

## Why

`scripts/speedrun.py` 只认模型注册表（registry）里的 400 类 base config：checkpoint 必须是 `pretrained` 或单一全局 `--checkpoint`，GT 只支持「UCF101 父目录名派生」。自己在数据集上微调出的模型（如 quadruped_cats_v1 的 TSM/SlowOnly/TimeSformer 5 类 ckpt）走不进标准管线——上次因此临时脚本绕行，丢失了标准标注（黑 margin + GT + top5）、封面、落盘约定（后补了三轮数据）。

## What Changes

- **speedrun.py 支持自定义 (config, checkpoint) 对**：新增 `--custom` 参数（或 manifest 文件），指定 per-model 的 mmaction2 config 路径 + checkpoint 路径，绕过 registry 解析
- **GT 从 ann_file 读取**：新增 `--ann-file` 参数（mmaction2 raw label 格式：`<video_path> <label_idx>`）+ `--label-map` 已有；命中时 `gt_label`/`correct` 填真值，未命中回退现有父目录派生逻辑
- **cats-v1-speedrun 批次重跑**：用标准管线对 3 模型 × 101 测试视频重新生成标注视频（覆盖 outputs/ 现有文件）与 results.json 记录
- 明确范围：不改 API（`/api/speedrun/run` 后续可加 custom 字段，本次不做）、不动 registry

## Capabilities

### Modified Capabilities
- `speedrun-results`（`openspec/specs/speedrun-results/`）：新增「自定义模型配置输入」与「GT 标注来源」要求

## Impact

- **脚本**：`scripts/speedrun.py`（argparse + GT 解析 + custom 分支，复用 `_infer.infer_and_annotate`）
- **数据**：pet `results/speedrun/outputs/<model>/*.mp4`（303 个重生成）+ `results.json`（303 条 metrics/output_video 更新，run_name 仍为 `cats-v1-speedrun`）
- **skill 文档**：新建 `.agents/skills/speedrun/`（权威入口）；testing/evaluation 改引用 + 修正 GT 描述；repo-structure 补 api/speedrun.js 与 SpeedRun.vue 归位、skill 表补行
