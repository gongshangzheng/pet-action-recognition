---
name: training
description: |
  训练 mmaction2 模型的操作指南。说明四种训练模式、如何触发训练（API/CLI）、checkpoint 产物、训练超参、远程执行闭环。
  触发场景：(1) 训练模型 (2) 断点续训 (3) 加载已有 checkpoint (4) finetune 预训练权重 (5) checkpoint 管理
---

# Training — mmaction2 训练操作指南

## 1. Overview

训练流程：`POST /api/training/run`（或 CLI `scripts/train_model.py`）→ 包装 `models/mmaction2/tools/train.py` → 产出 **checkpoint**（`latest.pth` + `best.pth`，软链到 `checkpoints/<model_id>/`）+ **指标**（`results/training/metrics.json`，含 `loss_series`）。

关键文件：
- `scripts/train_model.py` — 训练包装入口，构建 mmaction2 命令 + 解析产物 + 写 metrics。
- `server/routers/training.py` — `_MMACTION2_REGISTRY`（模型族清单）+ `/run` 端点 + checkpoint 管理。
- `server/config.py` — 路径常量（`CHECKPOINTS_DIR`、`TRAINING_DIR`、`MMACTION2_DIR` 等）。

## 2. 四种训练模式（互斥）

来源：`server/routers/training.py` `/run` 端点 + `scripts/train_model.py` argparse。

| 模式 | API 字段 | CLI flag | 行为 |
|------|---------|---------|------|
| 断点续训 | `resume_from`（或 `resume`） | `--resume <path\|auto>` | 复用 `run_id`，恢复 epoch/optimizer/scheduler；从 `checkpoints/<model_id>/<run_id>_latest.pth` 续训 |
| 加载已有 checkpoint | `load_from` | `--load-from <path\|run_id>` | 加载我们 checkpoint 的**权重**，epoch=0 从头训练（不恢复优化器状态） |
| finetune 预训练 | `pretrained`（`true` 用 registry URL，或填 URL/path） | `--pretrained <url\|path>` | 加载 backbone 预训练权重（mmaction2 模型仓库），finetune |
| 从零训练 | `from_scratch: true` | `--from-scratch` | 随机初始化，设 `model.backbone.init_cfg=None` 禁用 config 中任何预训练 |

> 四个模式互斥，只能选一个；都不选则用 config 默认值（registry 中模型默认带 K400 预训练）。
> `resume_from` 时若本地无 `latest.pth`，自动降级为 `--resume auto`（mmaction2 自动找 work_dir 内最新 checkpoint）。

## 3. 如何触发训练

### 3.1 API：`POST /api/training/run`

```json
{
  "model_id": "tsn-resnet50",
  "dataset_id": "quadruped_action",
  "epochs": 100,
  "lr": 1e-3,
  "batch_size": 16,
  "device": "cuda",
  "seed": 42,
  "pretrained": true,
  "extra_args": ""
}
```

断点续训示例：`{" "model_id": "tsn-resnet50", "resume_from": "train-tsn-resnet50-quadruped_action-1700000000"}`

返回：`{ "status": "started", "run_id", "pid", ... }`，训练后台运行，进度见 `GET /api/training/runs`。

### 3.2 CLI：`scripts/train_model.py`

```bash
python3 scripts/train_model.py \
  --model-id tsn-resnet50 \
  --dataset-id quadruped_action \
  --run-id train-$(date +%s) \
  --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
  --epochs 100 --lr 1e-4 --batch-size 16 --device cuda \
  --pretrained <url_or_path>
```

其他 CLI flag：`--num-classes`、`--seed`、`--work-dir`、`--extra-args`。`--mmaction2-config` 可传相对路径（相对 `MMACTION2_DIR` 或仓库根）或绝对路径，由 `resolve_mmaction2_config` 解析。

## 4. Checkpoint 产物

训练结束后，`scripts/train_model.py` 解析 mmaction2 `work_dir`，把 checkpoint 软链到 `checkpoints/<model_id>/`：

```
checkpoints/<model_id>/<run_id>_latest.pth   # 最新 epoch
checkpoints/<model_id>/<run_id>_latest.json  # 元数据
checkpoints/<model_id>/<run_id>_best.pth     # 验证最佳 epoch
checkpoints/<model_id>/<run_id>_best.json
```

JSON 元数据字段（`write_checkpoint_meta`）：

```json
{
  "run_id": "...",
  "model_id": "...",
  "dataset": "quadruped_action",
  "type": "latest | best | pretrained",
  "epoch": 95,
  "total_epochs": 100,
  "metrics": { "loss": 0.12, "top1_acc": 0.87, "top5_acc": 0.98, "lr": 1e-5 },
  "created_at": "2026-07-28T00:00:00Z",
  "checkpoint_path": "checkpoints/<model_id>/<run_id>_latest.pth",
  "source_file": "epoch_95.pth"
}
```

> 若无 val 阶段产出 best，则用 latest 充当 best（仅非 resume 情况）。
> resume 时若新 best top1 未超过旧 best，保留旧 best 不覆盖。

API：`GET /api/training/checkpoints`（读 JSON 元数据，旧 `.pth` 降级）、`GET /api/training/checkpoints/{id}`、`GET /api/training/outputs/{path}`（流式下载 `.pth`/`.log`）。

## 5. Metrics：`results/training/metrics.json`

`scripts/train_model.py` 把每个 run upsert 到 `metrics.json`：

```json
{
  "generated_at": "...",
  "runs": [
    {
      "id": "train-...",
      "model": "...", "dataset": "...",
      "status": "running | completed | error",
      "started_at": "...", "epochs": 100, "lr": 1e-3, "batch_size": 16, "device": "cuda",
      "checkpoint_path": "...", "best_checkpoint_path": "...",
      "metrics": { "latest_epoch": 95, "best_epoch": 88, "loss": ..., "top1_acc": ... },
      "best_metric": 0.87, "final_loss": 0.12,
      "loss_series": [{ "epoch": 1, "loss": 2.3, "top1_acc": 0.1, "lr": 1e-3 }, ...],
      "resumed_at | loaded_from | pretrained | from_scratch": "..."
    }
  ]
}
```

`loss_series` 由解析 mmaction2 `work_dir/vis_data/scalars.json`（每行一个 JSON）聚合而成。
轮询：`GET /api/training/runs`（可按 model/dataset/status 过滤）、`GET /api/training/runs/{run_id}`（含完整 loss_series）。

## 6. 训练 config preset

`DEFAULT_CONFIGS`（`server/routers/training.py`，`GET /api/training/configs`）：

| id | epochs | lr | batch_size | optimizer | scheduler | 用途 |
|----|--------|-----|-----------|-----------|-----------|------|
| `default` | 100 | 1e-3 | 16 | sgd | cosine | 动作识别默认超参；按模型/数据集调 |
| `fast` | 5 | 1e-3 | 4 | sgd | none | 5 epoch smoke，跑通 mmaction2 训练链路 |

> preset 仅为参考超参；实际 epochs/lr/batch_size 在 `/run` body 或 CLI flag 中覆盖。

## 7. 远程执行闭环（强制）

**训练必须在远程服务器（pet / A100）执行，绝不本地训练**（本地无 GPU、无 mmaction2 环境）。

```bash
# 1. 本地编辑代码
# 2. 推到 pet
git push pet main
# 3. ssh 上 pet，拉取最新
ssh pet
cd pet-action-recognition && git pull
# 4. 激活 conda 环境后触发训练（API 或 CLI）
conda activate pet   # py3.10 + torch2.1.2cu121 + mmcv2.1.0
# 5. 进度/loss 曲线通过 web 端口转发看：见 remote-servers skill
```

pet：2× RTX 4090，环境 `pet`。A100：≥4× A100-80GB，待启用。完整 SSH/端口转发/环境见 `.claude/skills/remote-servers/SKILL.md`，mmaction2 安装见 `.claude/skills/using-mmaction2/SKILL.md`。

## 8. Per-model label map（registry）

`_MMACTION2_REGISTRY` 中默认 label_map = Kinetics-400；以下模型带专属 `label_map` 字段（指向 `models/mmaction2/tools/data/` 下对应文件）：

| model_id | label_map | 预训练源 |
|----------|-----------|---------|
| `c3d-sports1m` | `tools/data/ucf101/label_map.txt` | UCF-101 (from Sports-1M) |
| `slowonly-resnet50` | `tools/data/kinetics/label_map_k700.txt` | Kinetics-700 |
| `trn-resnet50` | `tools/data/sthv2/label_map.txt` | Something-Something V2 |

其余模型（tsn/tsm/i3d/slowfast/r2plus1d/csn/tin/tpn/tanet/timesformer/mvit/swin/x3d/uniformer/videomae/videomaev2/c2d 等）默认 K400。

## 9. 常见坑

| 问题 | 原因 / 解决 |
|------|------|
| **CUDA OOM** | pet 2× 4090 GPU 共享，多人同时跑易爆显存；降 `batch_size`、`--num-workers`，或避开高峰期。见 remote-servers skill。 |
| **num_classes mismatch** | `model.cls_head.num_classes` 必须等于四足数据集类别数（读 `datasets/quadruped_action/classes.txt` 行数）；`train_model.py` 自动注入 `--num-classes`，并调整 `val_evaluator` topk（小数据集避免无意义 top5=1.0）。 |
| **decord / PyAV backend** | 不同模型 config 用不同 video decoder；缺包时换 backend 或装 `decord`/`av`。本地配置 `tsn-resnet50-quadruped` 用 PyAV。 |
| **mmcv 版本** | 必须 2.1.0，与 torch2.1.2cu121 配套；版本不匹配会报 `TypeError`/`AssertionError`。 |
| **训练模式互斥** | 一次只能选 resume/load_from/pretrained/from_scratch 之一，否则 `/run` 返回 400。 |
| **load_from 找不到** | `resolve_checkpoint_path` 按 `path` → `<model_id>/<id>_latest.pth` → 全局搜索顺序；未找到仅 warn 不阻塞。 |
