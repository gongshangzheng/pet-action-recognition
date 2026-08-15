# fix-speedrun-playback Design

## Context

见 proposal.md - Why。事实核查（已在 pet 验证）：
- 视频实际位置：`results/speedrun/{tsm-resnet50,slowonly-resnet50,timesformer-divst}/*.mp4`（各 101 个）
- `output_video` 现值：`results/speedrun/<model_id>/<stem>.mp4`（仓库相对）→ 前端拼成 `/api/speedrun/outputs/results/speedrun/...` → safe_resolve 404
- `cover_image`：303 条全缺
- 标准脚本落盘约定：`outputs/<model_id>/<stem>.mp4`，`output_video` 为 outputs 相对路径，封面在 `outputs/covers/<stem>.jpg`

## Goals / Non-Goals

**Goals**
- cats-v1-speedrun 303 条全部可播放 + 有封面
- speedrun 前端代码归属 evaluation 模块

**Non-Goals**
- 性能优化（mtime 缓存等，探索中另列）
- legacy 63 条历史记录的 output_video 修复（其值为 None，属更早的数据形态，本次不动）
- 后端 serve 逻辑改动

## Decisions

### D1: 移动文件而非软链
- `mv results/speedrun/<model>/ results/speedrun/outputs/<model>/`（outputs/ 下无同名目录，无冲突）
- 备选：软链兼容旧路径 → 拒绝，徒增复杂度；results.json 是唯一引用方，同步改路径即可

### D2: 封面用 ffmpeg 抽首帧
- `ffmpeg -i <mp4> -vframes 1 outputs/covers/<stem>.jpg`，与标准脚本封面策略一致（每视频一张、跨模型共用同名封面）
- 注意 cats 批次 3 个模型共享同一批 101 个源视频，封面按 stem 去重，只需抽 101 张

### D3: results.json 修补脚本在 pet 执行，备份后回写，再 rsync 回本地
- 与 run_name 补标同一模式（已有 .bak 先例）
- 修补内容：`output_video` 改为 `<model_id>/<stem>.mp4`；补 `cover_image: covers/<stem>.jpg`

### D4: 前端归位最小改动
- `git mv views/training/SpeedRun.vue views/evaluation/SpeedRun.vue`
- 新建 `api/speedrun.js` 承接 5 个 speedrun 函数；`api/training.js` 删除之；SpeedRun.vue import 改指向
- `router/index.js` 组件路径更新
- 理由：纯移动，无行为变化；归位后「路由模块 ↔ 代码目录」一致

## Risks / Trade-offs

- [移动文件时页面正在访问旧路径] → speedrun 无任务在跑，窗口风险可忽略；先改 results.json 再 mv，或先 mv 再改 json 都行（瞬间 404 可接受）
- [ffmpeg 抽帧对 4s 小视频很快（<1s/个）] → 101 个约 1-2 分钟
- [covers 目录已有 legacy 封面同名 stem] → cats 视频 stem 为 `event_2026*`，与 UCF101 的 `v_*` 不冲突

## Migration Plan

1. pet：mv 3 个模型目录进 outputs/
2. pet：ffmpeg 抽 101 张封面
3. pet：跑修补脚本更新 results.json（先备份）
4. 本地：rsync results.json 回本地
5. 本地：前端归位改动 → rsync 到 pet（vite 热更新）
6. 验证：页面选 cats-v1-speedrun，卡片出封面、点击可播放
