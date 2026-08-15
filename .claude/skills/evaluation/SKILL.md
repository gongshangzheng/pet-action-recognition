---
name: evaluation
description: |
  评测模块全景指南。说明评测模式怎么选（正式测试 / Speed Run / VLM / 单视频推理）、评测配置与模型/数据集管理（/api/evaluation/*）、VLM 对比评测、结果查看与对比。
  触发场景：(1) VLM 对比评测 (2) 查看评测结果 / 前端评测页 (3) 模型性能对比 / results compare (4) 评测配置、模型、数据集管理 (5) 分不清该用哪种评测模式。
  正式测试细节 → testing；Speed Run 细节 → speedrun。
---

# 评测体系模块全景

> **职责边界**：本 skill 管**评测模块全景**——模式选型、`/api/evaluation/*` 配置与模型/数据集管理、VLM 对比、结果查看与对比。
> 操作细节外派：**正式测试（top1/top5）→ [[testing]]**；**Speed Run（标注视频/烟测/run_name 批次）→ [[speedrun]]**。

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
│   ├── results.json           # Speed Run 聚合结果
│   └── outputs/               # 标注视频 + 封面
└── live/                      # Live 推理结果
```

## 评测模式总览（先分清用哪个）

| 模式 | 脚本 | 产物 | 用途 | 细节 |
|------|------|------|------|------|
| 正式测试 | `scripts/run_test.py` | `results/training/test_results.json` | top1/top5 准确率（全 test split） | **[[testing]]** |
| Speed Run | `scripts/speedrun.py` | `results/speedrun/` | 批量标注视频 + 烟测指标 | **[[speedrun]]** |
| VLM 测试 | `scripts/run_test_vlm.py` | JSON | Qwen3-VL-Plus 对比 | 本 skill §1 |
| 单视频推理 | `scripts/inference.py` | JSON | 单视频 top-k 预测 | **[[testing]]** |

选择：要**准确率数字** → 正式测试；要**标注视频/烟测/批次** → Speed Run；要**和 VLM 比对** → VLM 测试；只看**单个视频预测** → 单视频推理。

## 1. VLM 对比评测

集成 Qwen3-VL-Plus（DashScope API）进行对比评测。

### CLI

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

## 2. 评测模块管理（`/api/evaluation/*`）

评测模块自己的配置与产物服务（`server/routers/evaluation.py`）：

| 端点 | 说明 |
|------|------|
| `GET /api/evaluation/models`、`/models/{id}` | 模型定义列表/详情（`evaluation/models/*.json`） |
| `GET /api/evaluation/datasets`、`/datasets/{id}` | 数据集定义列表/详情（`evaluation/datasets/*.json`） |
| `GET /api/evaluation/configs`、`/configs/{id}` | 评测配置列表/详情（`evaluation/configs/*.json`） |
| `POST /api/evaluation/run` | 发起评测运行 |
| `GET /api/evaluation/outputs`、`/outputs/{path}` | 评测产物列表与文件服务 |
| `GET /api/evaluation/results`、`/results/{id}` | 评测结果列表/详情 |
| `GET /api/evaluation/results/compare` | 多模型结果对比 |

对应前端页面：`/evaluation/models`、`/evaluation/datasets`、`/evaluation/configs`、`/evaluation/run`、`/evaluation/outputs`（ModelManage / DatasetManage / ConfigManage / EvalRun / EvalOutputs）。

## 3. 查看评测结果

### API 端点

```bash
# 正式测试结果（testing 域）
GET /api/training/test_results

# Speed Run 结果（speedrun 域，支持 ?run_name= 批次过滤）
GET /api/speedrun/results

# Speed Run 标注视频流
GET /api/speedrun/outputs/{model_id}/{video_stem}.mp4

# 评测模块结果与对比（evaluation 域）
GET /api/evaluation/results
GET /api/evaluation/results/compare
```

### 前端页面

- `/evaluation/results` — 正式测试结果
- `/evaluation/speedrun` — Speed Run 页（视频画廊 + 批次筛选 + accuracy summary，详见 [[speedrun]] §8）
- `/training/results` — 训练结果（loss 曲线）

### 常用命令

```bash
# 过滤某模型的 speed run 结果
cat results/speedrun/results.json | jq '.[] | select(.model_id == "tsn-resnet50")'

# 按批次过滤（run_name）
cat results/speedrun/results.json | jq '.[] | select(.run_name == "cats-v1-speedrun")'
```

（per-model 准确率口径与 `correct` 匹配规则 → [[speedrun]] §5）

## 4. 与其他 skill 的关系

- **正式测试** = 训练完成后的验证（test split 上拿 top1/top5）→ [[testing]]
- **Speed Run** = 快速烟测 + 标注视频（任意视频，`--ann-file` 可给真 GT）→ [[speedrun]]
- **VLM 测试** = 基于提示词的方法对比 → 本 skill §1
- [[training]] — 训练模型、checkpoint 管理
- [[using-mmaction2]] — mmaction2 深度指南

> GPU 共享注意（pet 共享机、跑前 `nvidia-smi`、speedrun 串行）统一见 [[remote-servers]] 与 [[speedrun]] §9。
