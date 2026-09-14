---
name: evaluation
description: |
  评测体系模块操作指南。用于 mmaction2 模型评测、Speed Run、VLM 对比、数据集管理。
  触发场景：(1) 运行正式测试 (2) Speed Run 批量标注 (3) VLM 对比评测 (4) 查看评测结果 (5) 模型性能对比
---

# 评测体系模块 — mmaction2 动作识别评测

本 skill 提供评测体系模块的完整操作指南，包括正式测试、Speed Run、VLM 对比、结果管理。

## 项目结构

```
evaluation/                    # 评测配置目录
├── configs/                   # 评测配置 JSON
├── datasets/                  # 数据集定义 JSON
├── models/                    # 模型定义 JSON
├── outputs/                   # 评测产物（gitignore）
└── scripts/                   # 评测脚本（空壳）

results/
├── training/
│   ├── test_results.json      # 正式测试结果
│   ├── metrics.json           # 训练指标
│   └── checkpoints/           # 训练 checkpoint
├── speedrun/
│   ├── results.json            # Speed Run 聚合结果
│   └── outputs/               # 标注视频
└── live/                      # Live 推理结果
```

## 评测模式

| 模式 | 脚本 | 产物 | 用途 |
|------|------|------|------|
| 正式测试 | `scripts/run_test.py` | `results/training/test_results.json` | top1/top5 准确率 |
| Speed Run | `scripts/speedrun.py` | `results/speedrun/` | 批量标注视频 + 烟测指标 |
| VLM 测试 | `scripts/run_test_vlm.py` | JSON | Qwen3-VL-Plus 对比 |
| 单视频推理 | `scripts/inference.py` | JSON | 单视频预测 |

---

## 1. 正式测试（top1/top5 准确率）

### API：`POST /api/training/run_test`

```json
{
  "model_id": "tsn-resnet50",
  "checkpoint": "checkpoints/tsn-resnet50/train-1234567890_best.pth",
  "dataset_id": "quadruped_action",
  "split": "test",
  "device": "cuda:0"
}
```

### CLI（在 pet 上）

```bash
python scripts/run_test.py \
  --run-id test-1234567890 \
  --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
  --checkpoint results/training/checkpoints/tsn-resnet50/train-xxx_best.pth \
  --dataset-id quadruped_action --split test --device cuda:0
```

### 环境变量

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1  # PyTorch ≥2.6 需要
PYTHONPATH=models/mmaction2:repo_root
```

### 结果格式

```json
{
  "run_id": "test-1234567890",
  "model_id": "tsn-resnet50",
  "dataset_id": "quadruped_action",
  "split": "test",
  "status": "completed",
  "metrics": {
    "top1_acc": 0.87,
    "top5_acc": 0.97
  },
  "stdout_tail": "...",
  "finished_at": "2026-08-04T12:00:00"
}
```

---

## 2. Speed Run（批量标注视频）

### 特点

- **不需要标注文件**：直接喂视频路径，GT 从父目录名派生（仅 UCF101）
- **产出标注视频**：cv2 叠字版 H.264 mp4
- **每条结果即时落盘**：防长跑中途丢失

### API：`POST /api/speedrun/run`

```json
{
  "videos": ["/path/a.mp4", "/path/b.mp4"],
  "models": "all",
  "checkpoint": "pretrained",
  "device": "cuda:0",
  "force": false
}
```

### CLI（在 pet 上）

```bash
# 全部模型
python scripts/speedrun.py --videos a.mp4 b.mp4 --models all --device cuda:0

# 指定模型
python scripts/speedrun.py --videos a.mp4 --models tsn-resnet50 i3d-resnet50 --device cuda:0

# 强制重跑
python scripts/speedrun.py --videos a.mp4 --models tsn-resnet50 --force
```

### 产物

```
results/speedrun/
├── results.json              # 聚合所有 (model, video) 结果
└── outputs/
    └── <model_id>/
        └── <video_stem>.mp4  # 标注视频
```

### 结果字段

```json
{
  "id": "speedrun-tsn-resnet50-a",
  "model_id": "tsn-resnet50",
  "video": "/path/a.mp4",
  "checkpoint": "pretrained",
  "gt_label": "walk_dog",
  "correct": true,
  "metrics": {
    "top1_label": "walk_dog",
    "top1_score": 0.92,
    "top5": ["walk_dog", "jogging", "running", "walking", "standing"],
    "gpu_mem_mb": 2048,
    "elapsed_s": 1.23
  },
  "output_video": "tsn-resnet50/a.mp4",
  "status": "completed",
  "finished_at": "2026-08-04T12:00:00"
}
```

### 标注视频格式

- 上边条：`GT: <gt>`（绿）+ `pred: <label> (score)`（黄）
- 下边条：top5 列表
- 自动 H.264 转码（浏览器 `<video>` 只认 H.264）

### 正确率计算

`_matches(gt_label, top1_label)` 做 token-set 归一化匹配：
- camelCase 拆分 → lowercase → 排序
- 相等 → `correct=True`
- 任一为空 → `None`（不参与统计）

---

## 3. VLM 对比评测

集成 Qwen3-VL-Plus（DashScope API）进行对比评测。

### 脚本

```bash
python scripts/run_test_vlm.py \
  --videos /path/to/videos \
  --dataset-id quadruped_action \
  --output results/vlm_test.json
```

### API：`POST /api/training/run_test_vlm`

```json
{
  "videos": ["/path/a.mp4"],
  "dataset_id": "quadruped_action",
  "device": "cpu"
}
```

### 环境变量

```bash
DASHSCOPE_API_KEY=sk-xxx  # DashScope API Key
```

---

## 4. 查看评测结果

### API 端点

```bash
# 正式测试结果
GET /api/training/test_results

# Speed Run 结果
GET /api/speedrun/results

# Speed Run 标注视频流
GET /api/speedrun/outputs/{model_id}/{video_stem}.mp4

# 评测配置
GET /api/evaluation/configs
```

### 前端页面

- `/evaluation/results` — 正式测试结果
- `/evaluation/speedrun` — Speed Run 页面（视频画廊 + accuracy summary）
- `/training/results` — 训练结果（loss 曲线）

---

## 5. 模型性能对比

### Speed Run per-model 准确率

```python
# 从 results.json 聚合
per_model_correct = {}
per_model_total = {}
for r in results:
    if r['correct'] is not None:
        per_model_total[r['model_id']] = per_model_total.get(r['model_id'], 0) + 1
        if r['correct']:
            per_model_correct[r['model_id']] = per_model_correct.get(r['model_id'], 0) + 1

accuracy = {m: per_model_correct[m] / per_model_total[m] for m in per_model_total}
```

### Speed Run 烟测指标

| 指标 | 含义 |
|------|------|
| `gpu_mem_mb` | 峰值显存 |
| `elapsed_s` | 单 (model, video) 墙钟时间 |
| `correct` | 是否正确（token-set 归一化） |

---

## 6. GPU 共享注意

- **pet 是共享机**：跑前先 `nvidia-smi` 看卡
- `--device cuda:0` 或 `cuda:1` 选空闲卡
- Speed Run 串行跑，不要并行起多个

---

## 7. 常用命令

```bash
# 查看正式测试结果
cat results/training/test_results.json

# 查看 Speed Run 结果
cat results/speedrun/results.json

# 过滤某模型结果
cat results/speedrun/results.json | jq '.[] | select(.model_id == "tsn-resnet50")'

# 查看标注视频
ls results/speedrun/outputs/
```

---

## 8. 与 training skill 的关系

- **正式测试** = 训练完成后的验证（用 test split）
- **Speed Run** = 快速烟测（用任意视频，不需标注）
- **VLM 测试** = 基于提示词的方法对比

详见：
- [[training]] — 训练模型、checkpoint 管理
- [[testing]] — 测试/speed run 详细指南
- [[using-mmaction2]] — mmaction2 深度指南
