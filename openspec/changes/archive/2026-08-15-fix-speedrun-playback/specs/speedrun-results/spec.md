# speedrun-results Spec (delta)

## ADDED Requirements

### Requirement: 标注视频落盘约定

SpeedRun 标注视频 SHALL 落盘于 `results/speedrun/outputs/<model_id>/<video_stem>.mp4`，结果记录的 `output_video` 字段 SHALL 为相对于 `results/speedrun/outputs/` 的路径（如 `tsm-resnet50/xxx.mp4`），封面图 SHALL 落盘于 `results/speedrun/outputs/covers/` 且记录 `cover_image` 字段（同为 outputs 相对路径）。

#### Scenario: 结果记录可播放
- **WHEN** 一条结果记录的 `status` 为 `completed` 且标注视频已生成
- **THEN** 通过 `/api/speedrun/outputs/<output_video>` 能获取到该视频（HTTP 200）

#### Scenario: 结果记录有封面
- **WHEN** 一条结果记录引用了标注视频
- **THEN** 该记录包含 `cover_image` 字段且对应封面文件存在

### Requirement: 前端模块归属一致

SpeedRun 页面组件 SHALL 位于与其路由模块一致的目录（`evaluation/speedrun` 路由 ↔ `views/evaluation/`），speedrun API 封装 SHALL 位于独立模块（`api/speedrun.js`）。

#### Scenario: 按模块定位代码
- **WHEN** 开发者查找 SpeedRun 页面代码
- **THEN** 在 `web/src/views/evaluation/` 与 `web/src/api/speedrun.js` 找到全部相关代码，无 training 目录残留引用
