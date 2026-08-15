---
name: speedrun
description: |
  Speed Run（批量标注视频 + 烟测指标）的权威操作指南。说明 CLI（registry 模型 / --custom 微调模型）、GT 来源（--ann-file 优先）、run_name 批次、API、产物约定、correct 匹配、per-model label_map、黑 margin 标注格式、前端页、常见坑。
  触发场景：(1) 跑 speed run（registry 或微调模型）(2) 查看结果/标注视频 (3) 结果按批次筛选 (4) speed run 视频播不了/没标签 (5) 微调 checkpoint 想出标注视频
---

# Speed Run 权威指南

> 一切 speed run 都走 `scripts/speedrun.py` 标准管线。**绝不为微调模型写临时脚本绕行**——黑 margin 标注、封面、落盘约定、run_name 都由管线保证（历史教训：绕行一次，补了三轮数据）。

所有执行**只在 pet 远程**（conda env `pet`），本地仅编辑 + rsync。

## 1. 两种模型来源

| 来源 | 参数 | 适用 |
|---|---|---|
| Registry 模型 | `--models all` 或 `--models tsn-resnet50 i3d-resnet50` | K400 预训练权重（`checkpoints/<id>/<id>_pretrained.pth`） |
| **微调模型** | `--custom <model_id>=<config>:<ckpt>`（可重复） | 自有数据集训练的 checkpoint（如 quadruped_cats_v1 5 类） |

`--custom` 规则：
- 格式 `model_id=config路径:checkpoint路径`（config 在前，ckpt 在后）
- 与 registry 同 id 时**覆盖**同名 registry 条目（warn 提示）
- 只传 `--custom`（不传 `--models`）→ 仅跑 custom 模型；混传 `--models` → 两类合并跑
- config 需与 checkpoint 类数一致（微调模型用推断 config，见下）

微调模型的推断 config 生成：`results/training/overrides/inference/<model>-<dataset>_infer.py`（`model = dict(cls_head=dict(num_classes=N))` 模式，训练时自动产出）。

## 2. GT 来源（优先级）

1. **`--ann-file`**（raw label：`<video_path> <label_idx>`，每行一条）+ **`--label-map`**（每行一个类名）：按视频 stem 匹配 → `gt_label`/`correct` 填真值
2. 回退：父目录名派生（仅 UCF101 约定 `datasets/ucf101/<ClassName>/xxx.avi`）
3. 都没有 → `gt_label=None, correct=None`

自有数据集直接用现成文件：`datasets/<name>/annotation/test_public.txt` + `datasets/<name>/classes.txt`。

## 3. 批次（run_name）

- `--run-name <descriptor>`：标识一次运行批次（如 `cats-v1-speedrun`、`ucf101-baseline`）
- 缺省自动生成 `run-{YYYYMMDD-HHmm}`；历史无 run_name 记录读取时归 `legacy`
- 前端 Speed Run 页按批次筛选（与模型/视频筛选叠加），统计按筛选结果计算
- 同批次重跑：`--force` 覆盖旧视频，results.json 同 id 记录原地更新

## 4. 完整示例

```bash
# registry 全量（K400 模型 × UCF101）
python scripts/speedrun.py --videos datasets/ucf101/PlayingGuitar/v_xxx.avi \
  --models all --device cuda:0

# 微调模型 × 自有数据集（标准姿势）
python scripts/speedrun.py \
  --videos $(cat /tmp/cats_videos.txt | tr '\n' ' ') \
  --custom tsm-resnet50=results/training/overrides/inference/tsm-resnet50-quadruped_cats_v1_infer.py:results/training/work_dirs/train-tsm-.../best.pth \
  --custom slowonly-resnet50=...:....pth \
  --ann-file datasets/quadruped_cats_v1/annotation/test_public.txt \
  --label-map datasets/quadruped_cats_v1/classes.txt \
  --run-name cats-v1-speedrun \
  --device cuda:0 --force
```

API：`POST /api/speedrun/run`（body: `videos/models/checkpoint/device/force/run_name`；custom 模型暂不支持 API，用 CLI）。

## 5. 产物约定（勿绕过）

```
results/speedrun/
├── results.json               # 每 (model, video) 一条，跑完即落盘
└── outputs/
    ├── <model_id>/<stem>.mp4  # H.264 标注视频（黑 margin 版）
    └── covers/<stem>.jpg      # 封面（同 stem 跨模型共用，自动抽取）
```

`results.json` 每条：`id`（`speedrun-<model>-<stem>`）、`model_id`、`video`、`checkpoint`、`run_name`、`gt_label`、`correct`（token-set 归一化比对）、`metrics`（`top1_label/top1_score/top5/gpu_mem_mb`）、`output_video`（**outputs/ 相对路径**，如 `tsm-resnet50/x.mp4`）、`cover_image`、`status`、`rtf`、`gpu_mem_mb`、`finished_at`。

**`correct` 匹配（`_matches`，token-set 归一化）**：
- `_norm_tokens`：拆 camelCase（`PlayingGuitar` → `Playing Guitar`）→ 拆非字母数字 → lowercase → 排序成 tuple
- GT 与 pred 的 token tuple 相等 → `correct=True`；任一为空 → `None`（N/A，不参与统计）
- 目的：跨数据集类名风格匹配（UCF101 `PlayingGuitar` vs K400 `playing guitar`）
- **per-model 准确率 = correct=True 数 / correct 非 None 总数**

指标定义：`gpu_mem_mb` = 峰值显存（`torch.cuda.max_memory_allocated`）；`elapsed_s` = 单 (model,video) 墙钟。

## 6. 标注视频格式（`_infer._annotate_video_cv2`）

- 上下黑 margin 边条，原帧居中不动（字不遮画面）
- 上边条：`GT: <gt>`（绿）+ `pred: <label> (score)`（黄）
- 下边条：top5 列表（白），`1. label 0.xx`
- cv2 写 `mp4v` → `_transcode_h264` 用 `imageio_ffmpeg`（moviepy 自带 libx264）转 H.264 + yuv420p + 去音轨；浏览器 `<video>` 只认 H.264，这步必须
- ffmpeg 不可用时降级为 mp4v 重命名（文件在但可能播不了）
- http(s) 视频不支持出标注视频（抛 `NotImplementedError`）

## 7. Per-model label_map（registry 模型）

registry 模型的标签名按 **per-model label_map** 解析（`_MMACTION2_REGISTRY` 条目，缺省 K400）；`--custom` / `--ann-file` 场景用 `--label-map` 显式指定（见 §2）。

| model_id | label_map |
|---|---|
| `c3d-sports1m` | `models/mmaction2/tools/data/ucf101/label_map.txt`（UCF101） |
| `slowonly-resnet50` | `.../kinetics/label_map_k700.txt`（K700） |
| `trn-resnet50` | `.../sthv2/label_map.txt`（SSv2） |
| 其余 recognition | 默认 K400 `.../kinetics/label_map_k400.txt` |

`_labels_for(model_entry)` 读 `model_entry["label_map"]`（相对路径基于 REPO，按文件路径缓存）；`load_labels`（`_infer.py`）按行读，index=行号（mmaction2 约定）。

## 8. 前端 Speed Run 页（`/evaluation/speedrun`）

- 视频画廊：n-grid 卡片，每卡播放标注视频 + ✓/✗ badge（`correct`）
- 过滤：按 model、按 video、按 run_name 批次（可叠加）；统计按筛选后数据计算
- 分页 20/页；顶部 per-model accuracy summary
- 数据：`GET /api/speedrun/results`（支持 `?run_name=`）+ `GET /api/speedrun/outputs`；视频经 `GET /api/speedrun/outputs/<model>/<stem>.mp4` 流式服务（video MIME，`safe_resolve` 防穿越）

## 9. 执行约束

- **串行单进程**（N 视频 × M 模型）；不要并行起多个 speedrun——路由用模块级单例 `_current_proc` 跟踪，多开会乱
- pet 共享机：跑前必先 `nvidia-smi`，`--device cuda:0/1` 选空闲卡

## 10. 常见坑

| 坑 | 症状 | 解法 |
|---|---|---|
| registry 只认 400 类 | 微调 ckpt 报 fc_cls shape mismatch | 用 `--custom` 传 (config, ckpt) 对 |
| 绕管线写临时脚本 | 没黑 margin/没封面/路径错 | **禁止**；改用 `--custom` 走标准管线 |
| GPU 被占 | detection 模型 OOM | 跑前 `nvidia-smi` 看空卡，`--device cuda:0/1`；共享机注意他人进程 |
| 视频播不了 | 浏览器黑屏 | 确认 H.264（`_transcode_h264` 正常路径已保证） |
| label_map 顺序不一致 | correct 全 False | `--label-map` 必须用训练时同一份 classes.txt |
| 并行起多个 speedrun | 路由 `_current_proc` 状态错乱 | 串行跑，一次一个批次 |

## 11. 相关

- [[testing]] — 正式测试 / 单视频推理（与本 skill 的职责边界见其开头）
- [[evaluation]] — 评测模块全景（Speed Run 在评测页展示）
- [[remote-servers]] — pet 环境、GPU 共享、开发闭环
- 前端：`web/src/views/evaluation/SpeedRun.vue` + `web/src/api/speedrun.js`
