# fix-speedrun-playback Proposal

## Why

`cats-v1-speedrun` 批次的 303 条结果在 SpeedRun 页全部无法播放、无封面：当时用自定义脚本跑批，标注视频落盘在 `results/speedrun/<model_id>/`（标准约定是 `results/speedrun/outputs/<model_id>/`），`output_video` 字段写的是仓库相对路径而非 outputs 相对路径，`cover_image` 字段完全缺失。同时 speedrun 模块代码归属混乱：路由挂在 `evaluation/speedrun`，页面组件却在 `views/training/`，API 封装在 `api/training.js`。

## What Changes

- **数据修复**：pet 上 3 个模型目录的 303 个标注视频移动到 `results/speedrun/outputs/<model_id>/`；`results.json` 中 cats 记录的 `output_video` 改为 outputs 相对路径；从每个视频提取首帧生成封面到 `outputs/covers/` 并补 `cover_image` 字段
- **组织归位**：`views/training/SpeedRun.vue` → `views/evaluation/SpeedRun.vue`；`api/training.js` 中 speedrun 相关 5 个函数拆到 `api/speedrun.js`；更新 router 与 import 引用
- 明确范围假设：本变更**不含**性能优化（mtime 缓存、results.json 分文件等探索中讨论的方向），那些另行提案

## Capabilities

### Modified Capabilities
- `speedrun-results`: 补充产物落盘约定与播放/封面可用性要求（由 fix-speedrun-playback 引入的 delta）

## Impact

- **数据**：pet `results/speedrun/` 目录结构 + `results.json`（有 .bak 备份），同步回本地
- **前端**：`web/src/views/evaluation/SpeedRun.vue`（移动）、`web/src/api/speedrun.js`（新建）、`web/src/router/index.js`、引用方 import 更新
- **无后端代码改动**（serve 逻辑不变，数据归位后即可用）
