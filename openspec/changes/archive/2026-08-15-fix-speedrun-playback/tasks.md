# fix-speedrun-playback Tasks

## 数据修复（pet）

- [x] **T1** 移动标注视频：`results/speedrun/{tsm-resnet50,slowonly-resnet50,timesformer-divst}/` → `results/speedrun/outputs/` 下同名目录
- [x] **T2** 抽封面：对 101 个去重 stem 用 ffmpeg 抽首帧 → `outputs/covers/<stem>.jpg`
- [x] **T3** 修补 results.json：cats 记录 `output_video` 改 outputs 相对路径、补 `cover_image`（先备份）；rsync 回本地

## 前端归位（本地 → rsync pet）

- [x] **T4** `git mv web/src/views/training/SpeedRun.vue web/src/views/evaluation/SpeedRun.vue`；新建 `web/src/api/speedrun.js` 承接 5 个 speedrun API 函数；`api/training.js` 删除对应函数；更新 SpeedRun.vue 与 `router/index.js` 的 import

## 验证

- [x] **T5** 页面选 `cats-v1-speedrun`：卡片显示封面、点击可播放；API 抽查 `/api/speedrun/outputs/tsm-resnet50/<stem>.mp4` 返回 200
