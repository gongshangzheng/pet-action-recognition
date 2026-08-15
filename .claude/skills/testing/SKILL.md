---
name: testing
description: |
  mmaction2 正式测试与单视频推理指南。说明 run_test.py（top1/top5 准确率）、inference.py（单视频 top-k JSON）、远程执行闭环、GPU 共享注意。
  触发场景：(1) 跑测试拿准确率 (2) 单视频推理 (3) 查看测试/推理结果 (4) GPU 显存/耗时分析。
  Speed Run（标注视频/烟测/批次）不归本 skill —— 用 speedrun。
---

# mmaction2 正式测试 / 单视频推理

> **职责边界**：本 skill 只管 **正式测试**（`run_test.py`，top1/top5 准确率）和 **单视频推理**（`inference.py`，JSON top-k）。
> **Speed Run（标注视频 + 烟测指标 + `--custom` + run_name 批次）的一切细节 → [[speedrun]]**（权威入口）。

mmaction2 vendor 在 `models/mmaction2/`。所有测试/推理**只在 pet 远程跑**（2× RTX 4090，conda env `pet`），本地仅编辑+push。

## 1. 三种模式（先分清用哪个）

| 模式 | 脚本 | 产物 | 回答什么 |
|---|---|---|---|
| 正式测试 | `scripts/run_test.py` | `results/training/test_results.json` | top1/top5 准确率（全 test split，需 ann_file） |
| 单视频推理 | `scripts/inference.py` | JSON（`results/training/inference/<run_id>.json`） | 一个视频的 top-k 预测，不出标注视频 |
| Speed run | `scripts/speedrun.py` | `results/speedrun/` | 标注视频 + 烟测指标 → **[[speedrun]]** |

选择：要**准确率数字** → 正式测试；要看**单个视频的预测** → 单视频推理；要**标注视频 / 快速烟测 / 批次管理** → speed run。

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

## 3. 单视频推理（JSON-only）

`scripts/inference.py`——一个视频的 top-k 预测，**不出标注视频、不写 speedrun results**（要标注视频 → [[speedrun]]）。

```bash
python scripts/inference.py \
  --video <video.mp4> \
  --checkpoint <ckpt.pth> \
  --mmaction2-config <config.py> \
  --labels datasets/<ds>/classes.txt \
  --num-classes 5 \
  --device cuda:0 \
  --output /tmp/pred.json
```

- `--labels` **建议显式传**：缺省会回退到四足数据集 classes（`QUADRUPED_CLASSES_FILE`），跑其他数据集模型不传会标错名
- `--num-classes` 给定时收窄 top-k（微调小类数模型避免无意义的 top5）
- API：`POST /api/training/inference`（后台运行）→ `GET /api/training/inference/{run_id}` 取结果，落盘 `results/training/inference/<run_id>.json`

## 4. 远程执行闭环（MUST）

**绝不在本地跑测试/推理**（本地无 GPU、无 mmaction2 依赖、MPS 不支持 float64）。流程：

1. 本地编辑代码 → `git push pet main`
2. `ssh pet` → `cd ~/pet-action-recognition && git pull`
3. `conda activate pet`
4. 先 `nvidia-smi` 看显存（pet 是共享机）→ 选 `--device cuda:0` 或 `cuda:1`
5. 跑 `python scripts/run_test.py ...` 或 `python scripts/inference.py ...`（speed run 见 [[speedrun]]）
6. 长跑建议进 tmux；产物落盘后本地 `git pull` 同步 results/，或前端直接看结果。

## 5. GPU 共享注意

- pet 2× 4090 但多用户共用。跑前 **必先** `nvidia-smi`。
- `--device cuda:0` / `cuda:1` 选空闲卡；显存够再跑。
- speedrun 的串行约束与 `gpu_mem_mb`/`elapsed_s` 指标定义 → [[speedrun]] §9。

## 关键文件路径

- `scripts/run_test.py` — 正式测试包装
- `scripts/inference.py` — 单视频推理（JSON-only，无标注视频）
- `scripts/_infer.py` — 共享推理内核 + cv2 标注 + H.264 转码（标注格式 / correct 匹配 / label_map 细节见 [[speedrun]]）
- `server/routers/training.py` — `/run_test`、`/inference`、`/test_results`、`/outputs`、`_MMACTION2_REGISTRY`
- 产物：`results/training/test_results.json`、`results/training/inference/`
