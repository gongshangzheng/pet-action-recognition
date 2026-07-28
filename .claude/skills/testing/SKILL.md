---
name: testing
description: |
  测试/评测/speed run mmaction2 模型的操作指南。说明正式测试（top1/top5 准确率）、speed run（标注视频+烟测指标）、推理（单视频）、远程执行闭环。
  触发场景：(1) 跑测试拿准确率 (2) speed run 看标注视频 (3) 单视频推理 (4) 查看测试/speed run 结果 (5) GPU 显存/耗时分析
---

# mmaction2 测试 / 评测 / Speed Run

mmaction2 vendor 在 `models/mmaction2/`。所有测试/推理**只在 pet 远程跑**（2× RTX 4090，conda env `pet`），本地仅编辑+push。

## 1. 两种测试模式

| 模式 | 脚本 | 产物 | 回答什么 |
|---|---|---|---|
| 正式测试 | `scripts/run_test.py` | `results/training/test_results.json` | top1/top5 准确率（在 test split 上） |
| Speed run | `scripts/speedrun.py` | `results/speedrun/outputs/<model>/<video>.mp4` + `results/speedrun/results.json` | 标注视频 + 烟测指标（top1/gpu_mem/elapsed/correct） |
| 单视频推理 | `scripts/inference.py` | JSON（`results/training/inference/<run_id>.json`） | 一个视频的 top-k 预测，不出标注视频 |

核心区别：正式测试需要 `ann_file` 标注文件跑全 split；speed run 不需标注，直接喂视频路径，GT 从父目录名派生（仅 UCF101）。

## 2. 正式测试（top1/top5）

**CLI**（在 pet 上）：
```bash
python scripts/run_test.py \
  --run-id test-1234567890 \
  --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
  --checkpoint results/training/checkpoints/<model>/<ckpt>.pth \
  --dataset-id quadruped_action --split test --device cuda
```

**API**：`POST /api/training/run_test`
```json
{"model_id": "tsn-resnet50", "checkpoint": "checkpoints/...", "dataset_id": "quadruped_action", "split": "test", "device": "cuda"}
```

流程（`run_test.py`）：
1. 按 split 定位 ann_file / data_root（`<dataset>_<split>_list.txt` + `videos_<split>/`）。缺标注 → 写 error 结果返回。
2. subprocess 调 `models/mmaction2/tools/test.py`，通过 `--cfg-options` 覆盖 `test_dataloader.dataset.ann_file` / `data_prefix.video`；若 `--num-classes` 给定则同时收窄 `top_k_accuracy.topk`（避免小数据集上报无意义的 top5）。
3. `parse_metrics` 正则扫 stdout 的 `acc/top1` / `acc/top5` → 写 `results/training/test_results.json`（按 run_id upsert，含 `metrics` / `stdout_tail` / `status`）。

环境：`TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`（PyTorch ≥2.6 默认 weights_only=True 会因 mmengine 的 HistoryBuffer 失败）；`PYTHONPATH` 含 `MMACTION2_DIR + REPO`。`--device cpu` 时注入 sitecustomize 关掉 MPS（macOS）。

**前端**：评测结果页 `EvalResults.vue` 读 `GET /api/training/test_results`。

## 3. Speed Run（标注视频 + 烟测）

**CLI**（在 pet 上）：
```bash
python scripts/speedrun.py --videos a.mp4 b.mp4 --models all --device cuda:0 --force
python scripts/speedrun.py --videos a.mp4 --models tsn-resnet50 i3d-resnet50
```

**API**：`POST /api/speedrun/run`
```json
{"videos": ["/path/a.mp4"], "models": "all", "checkpoint": "pretrained", "device": "cuda:0", "force": false}
```

关键参数：
- `--models all` → registry 全体**排除** `*-quadruped` 变体（那是四足数据集专用 config，非独立模型）。也可传 model_id 列表。
- `--checkpoint pretrained`（默认）→ 用 `checkpoints/<model_id>/<model_id>_pretrained.pth`（需已下好）；缺权重的模型跳过并 warn。
- `--force` → 重跑已存在的（默认 `os.path.isfile(out_video)` 即跳过，但 results.json 仍补 skipped 记录）。
- `--device cuda:0` / `cpu`。

产物（路径由约定派生，不传 arg）：
- `results/speedrun/outputs/<model_id>/<video_stem>.mp4` — H.264 标注视频
- `results/speedrun/results.json` — 每个 (model, video) 一条，**每跑完一条即落盘**（防长跑中途丢失）

`results.json` 每条字段：`id`（`speedrun-<model>-<stem>`）、`model_id`、`video`、`checkpoint`、`gt_label`、`correct`（bool/None）、`metrics`（`{top1_label, top1_score, top5, gpu_mem_mb}`）、`output_video`（相对 `outputs/`，形如 `<model>/<stem>.mp4`）、`status`、`gpu_mem_mb`、`elapsed_s`、`finished_at`。

**前端**：Speed Run 页 `/evaluation/speedrun`，读 `GET /api/speedrun/results` + `GET /api/speedrun/outputs`。视频通过 `GET /api/speedrun/outputs/<model>/<stem>.mp4` 流式服务（video MIME，`safe_resolve` 防穿越）。

## 4. 标注视频格式

`_infer._annotate_video_cv2`：
- 上下加 margin 边条，原帧居中不动（字不遮画面）。
- 上边条：`GT: <gt>`（绿）+ `pred: <label> (score)`（黄）。
- 下边条：top5 列表（白），`1. label 0.xx`。
- cv2 写 `mp4v` → `_transcode_h264` 用 `imageio_ffmpeg`（moviepy 自带 libx264）转 H.264 + yuv420p + 去音轨。浏览器 `<video>` 只认 H.264，所以这步必须。ffmpeg 不可用时降级为 mp4v 重命名（文件在但可能播不了）。
- http(s) 视频不支持出标注视频，会抛 `NotImplementedError`。

## 5. `correct` 字段（准确率）

`speedrun._matches(gt_label, top1_label)` 做 **token-set 归一化匹配**：
- `_norm_tokens`：拆 camelCase（`PlayingGuitar` → `Playing Guitar`）→ 拆非字母数字 → lowercase → 排序成 tuple。
- GT 与 pred 的 token tuple 相等 → `correct=True`；任一为空 → `None`（N/A，不参与统计）。
- 目的：跨数据集类名风格匹配（UCF101 `PlayingGuitar` vs K400 `playing guitar`）。
- **per-model 准确率 = correct=True 数 / (correct 非None 总数)**。

## 6. Speed Run 页 UI

- 视频画廊：n-grid 卡片，每卡播放标注视频 + ✓/✗ badge（`correct`）。
- 过滤：按 model、按 video。
- 分页：20/页。
- 顶部：per-model accuracy summary。

## 7. 远程执行闭环（MUST）

**绝不在本地跑测试/推理**（本地无 GPU、无 mmaction2 依赖、MPS 不支持 float64）。流程：

1. 本地编辑代码 → `git push pet main`
2. `ssh pet` → `cd ~/pet-action-recognition && git pull`
3. `conda activate pet`
4. 先 `nvidia-smi` 看显存（pet 是共享机）→ 选 `--device cuda:0` 或 `cuda:1`
5. 跑 `python scripts/run_test.py ...` 或 `python scripts/speedrun.py ...`
6. 长跑建议进 tmux；产物落盘后本地 `git pull` 同步 results/，或前端直接看 `GET /api/speedrun/results`。

## 8. Per-model label_map

speedrun 用 **per-model** `label_map`（从 `_MMACTION2_REGISTRY` 取，缺省 K400）：

| model_id | label_map |
|---|---|
| `c3d-sports1m` | `models/mmaction2/tools/data/ucf101/label_map.txt`（UCF101） |
| `slowonly-resnet50` | `.../kinetics/label_map_k700.txt`（K700） |
| `trn-resnet50` | `.../sthv2/label_map.txt`（SSv2） |
| 其余 | 默认 K400 `.../kinetics/label_map_k400.txt` |

`_labels_for(model_entry)` 读 `model_entry["label_map"]`，相对路径基于 REPO；按文件路径缓存。`load_labels`（`_infer.py`）按行读，index=行号（mmaction2 约定）。

## 9. GPU 共享注意

- pet 2× 4090 但多用户共用。跑前 **必先** `nvidia-smi`。
- `--device cuda:0` / `cuda:1` 选空闲卡；显存够再跑。
- speedrun 串行跑（N 视频 × M 模型），单进程；不要并行起多个 speedrun（路由用模块级单例 `_current_proc` 跟踪，多开会乱）。
- `gpu_mem_mb` 是峰值显存（`torch.cuda.max_memory_allocated`），`elapsed_s` 是单 (model,video) 墙钟。

## 关键文件路径

- `scripts/run_test.py` — 正式测试包装
- `scripts/speedrun.py` — speed run 批量
- `scripts/_infer.py` — 共享推理 + cv2 标注 + H.264 转码
- `scripts/inference.py` — 单视频推理（JSON-only，无标注视频）
- `server/routers/training.py` — `/run_test`、`/inference`、`/test_results`、`/outputs`、`_MMACTION2_REGISTRY`
- `server/routers/speedrun.py` — `/speedrun/run`、`/results`、`/outputs`、`/status`
- 产物：`results/training/test_results.json`、`results/training/inference/`、`results/speedrun/outputs/`、`results/speedrun/results.json`
