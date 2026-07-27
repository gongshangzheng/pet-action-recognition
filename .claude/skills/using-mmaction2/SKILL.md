---
name: using-mmaction2
description: |
  在 pet-action-recognition 训练框架下使用 mmaction2 的指南。说明 mmaction2 的安装、config 系统（_base_ 继承）、训练入口（tools/train.py）、如何把数据集与模型适配到我们的训练 registry，以及与 server/routers/training.py + results/training/ + web 训练页的对接。
  触发场景：(1) 训练/调用 mmaction2 模型 (2) 把新模型族注册进训练 registry (3) 适配四足动物数据集到 mmaction2 (4) 排查 mmaction2 训练报错 (5) 升级 models/mmaction2 vendor
---

# 在本仓库使用 mmaction2

mmaction2 = OpenMMLab 视频动作识别库。**已 vendor 进仓库**：`models/mmaction2/`（shallow clone，HEAD `a5a167d`，见 `models/README.md`）。不是 pip 依赖、不是 submodule —— 文件直接在本仓库历史里。

## 1. 安装

mmaction2 依赖 mmengine + mmcv + torch + decord。**已验证配方（pet 服务器，2× RTX 4090，2026-07-26 跑通）**：

```bash
# 在 conda env `pet`（python 3.10）里
ENV=~/miniconda3/envs/pet
PIP=$ENV/bin/pip; MIM=$ENV/bin/mim; PY=$ENV/bin/python

# 1) torch 2.1.2 + cu121（4090 兼容；且有对应 mmcv 2.x prebuilt wheel）
$PIP install --no-cache-dir torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121

# 2) openmim + mmengine + mmcv（mmcv 必须 <2.2.0，见下坑2）
$PIP install -U openmim
$MIM install mmengine "mmcv>=2.0.0rc4,<2.2.0"

# 3) decord + 其余依赖；opencv 必须 4.10.0.84（见下坑3）
$PIP install --no-cache-dir decord einops "opencv-python==4.10.0.84" "opencv-contrib-python==4.10.0.84" scipy matplotlib av

# 4) editable 装 vendor 的 mmaction2（改 models/mmaction2 源码即时生效）
$PIP install -v -e models/mmaction2

# 5) 验证
$PY -c "import torch,mmcv,mmengine,mmaction,decord; print(torch.__version__, torch.cuda.is_available(), mmcv.__version__, mmaction.__version__); print(torch.cuda.device_count())"
```

### ⚠️ 三大版本坑（pet 实踩，按此配方可避开）

1. **numpy 必须 <2** —— torch 2.1.2 是按 numpy 1.x 编的，numpy 2.x 会 `_ARRAY_API not found`，`tensor.numpy()` 在数据管线里崩。装完全栈后**最后**钉一次：`pip install "numpy<2"`（1.26.4）。
2. **mmcv 必须 `<2.2.0`** —— mmaction2 1.2.0 源码 assert `mmcv>=2.0.0rc4, <2.2.0`；`mim install "mmcv>=2.0.0"` 会拉 2.2.0 → import 时 AssertionError。用 `mim install "mmcv>=2.0.0rc4,<2.2.0"`（落 2.1.0）。
3. **opencv 钉 `4.10.0.84`** —— opencv 5.x / 4.13+ 的 metadata 声明 `numpy>=2`，pip 装它们会把 numpy 顶回 2.x。钉 4.10.0.84（声明 `numpy>=1.21.2`）才能让 numpy 1.26.4 稳住。

> `pip check` 会报 `decord 0.6.0 is not supported on this platform` —— spurious（metadata 保守），import 正常，忽略。
>
> 若 decord 装不上（macOS / 老 Python），用 PyAV 后端：`pip install av`，config 里 `DecordInit` 换 `AVInit`。训练报 `No module named 'mmcv'` → `mim install mmcv`；报 `MMCV_WITH_OPS=0` → 装 prebuilt mmcv（2.x 用 `mmcv`，对 cu121/torch2.1 走 `mim install` 自动选 wheel）。

### pet 环境速查

| 包 | 版本 |
|---|---|
| python | 3.10（conda env `pet`） |
| torch | 2.1.2+cu121 |
| numpy | 1.26.4（**<2**） |
| mmcv | 2.1.0（**<2.2.0**） |
| opencv | 4.10.0.84 |
| mmengine / mmaction2 / decord | 0.10.7 / 1.2.0 (editable) / 0.6.0 |

## 2. config 系统（python config + `_base_` 继承）

mmaction2 用 mmengine 的 `Config`：config 是 python 文件，靠 `_base_` 列表做多层继承。一个典型训练 config（如 `configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py`）只是三块拼装：

```python
_base_ = [
    '../../_base_/models/tsn_r50.py',       # 模型定义 (Recognizer2D + ResNet + TSNHead)
    '../../_base_/schedules/sgd_100e.py',   # 优化器/lr/epoch/钩子
    '../../_base_/default_runtime.py',     # 运行时（日志/checkpoint/runner）
]
# 下面只覆盖 dataset settings + pipeline
dataset_type = 'VideoDataset'
data_root = 'data/kinetics400/videos_train'
ann_file_train = 'data/kinetics400/kinetics400_train_list_videos.txt'
train_pipeline = [ dict(type='DecordInit', ...), dict(type='SampleFrames', clip_len=1, ...), ... ]
```

三个 `_base_` 子目录：
- `configs/_base_/models/*.py` — `model = dict(type='Recognizer2D', backbone=..., cls_head=..., data_preprocessor=...)`。已含：c2d/c3d/i3d/mvit/r2plus1d/slowfast/slowonly/swin/tanet/tin/tpn/trn/tsm/tsn/x3d 等。
- `configs/_base_/schedules/*.py` — `optim_wrapper`/`param_scheduler`/`train_cfg`（epoch 数、lr、warmup）。
- `configs/_base_/default_runtime.py` — `default_hooks`/`vis_backends`/`env_cfg`。

**改模型只改 `_base_/models/*.py` 或在 config 里覆盖 `model = dict(..., cls_head=dict(num_classes=N))`**，不动源码。

## 3. 训练入口与四种模式

训练通过 `scripts/train_model.py`（由 `POST /api/training/run` 触发），最终调用 `models/mmaction2/tools/train.py`。

### 四种训练模式（互斥，API body / CLI 只能选一个）

| 模式 | API 字段 | CLI 参数 | 说明 |
|------|---------|---------|------|
| 默认 | （不传） | （不传） | 使用 config 中已有的 `init_cfg` / `load_from` |
| 预训练 finetune | `pretrained: true` 或 `"<url\|path>"` | `--pretrained <url\|path>` | `true` 自动从注册表解析 mmaction2 模型仓库 URL；也可传自定义 URL 或本地路径。通过 `load_from` 加载全部可匹配权重（backbone + head），head 维度不匹配时自动跳过 |
| 加载权重从头训 | `load_from: "<checkpoint\|run_id>"` | `--load-from <path\|run_id>` | 加载我们已有 checkpoint 的全部权重，重置 epoch=0 / optimizer / scheduler |
| 断点续训 | `resume_from: "<run_id>"` | `--resume <path>` | 复用原 run_id，恢复 epoch / optimizer / scheduler；完成后覆盖 latest，best 仅在更优时覆盖 |
| 从头训练 | `from_scratch: true` | `--from-scratch` | 随机初始化，禁用 config 中的 `init_cfg` |

### Checkpoint 产物结构

所有 checkpoint（trained + pretrained）统一在 repo 根 `./checkpoints/<model_id>/`：

```
checkpoints/<model_id>/
  <model_id>_pretrained.pth        # mmaction2 模型仓库下载的预训练权重（finetune 用）
  <model_id>_pretrained.json       # type=pretrained；含 url/sha256/size；不被 latest/best 收录
  <run_id>_latest.pth              # → work_dir/epoch_N.pth（训练产物）
  <run_id>_latest.json             # {run_id, model_id, dataset, type, epoch, total_epochs, metrics, created_at, source_file}
  <run_id>_best.pth                # → work_dir/best_acc_top1_epoch_N.pth
  <run_id>_best.json               # 同上，type=best
```

> trained 与 pretrained 同处一个 `<model_id>/` 子目录，靠 JSON 的 `type` 字段区分（`latest`/`best`/`pretrained`）。`_trained_checkpoints_for` 只收 latest/best，pretrained 被忽略。`GET /api/training/outputs` 列出所有；`/outputs/checkpoints/...` 路径前缀解析到 `./checkpoints/`。

### 下载 pretrained checkpoint

```bash
# 单个模型
python3 scripts/download_checkpoint.py --model-id tsn-resnet50
# 全部 21 个
python3 scripts/download_checkpoint.py --all
# 重下
python3 scripts/download_checkpoint.py --model-id tsn-resnet50 --force
# 列出可用模型
python3 scripts/download_checkpoint.py --list
```

- 从 `_MMACTION2_REGISTRY` 的 `pretrained_url` 下到 `./checkpoints/<model_id>/<model_id>_pretrained.pth`
- 镜像回退：openmmlab 直链（pet 实测可达）；`huggingface.co` URL 自动走 `hf-mirror.com`
- 失败重试 3 次；已存在则跳过（`--force` 强制重下）
- 元数据 `.json` 含 `url`、`sha256`、`size_bytes`、`type:"pretrained"`
- finetune 时传相对路径（脚本 cwd=repo 根）：`POST /api/training/run {model_id, pretrained: "checkpoints/<model_id>/<model_id>_pretrained.pth"}`

### 训练 run 记录（metrics.json）

每个 run 记录训练模式标记：`resumed_at`、`loaded_from`、`pretrained`、`from_scratch`。

## 4. 适配四足动物数据集

数据集根目录由变量 `QUADRUPED_DATASET_NAME`（`server/config.py`）决定 → `datasets/<QUADRUPED_DATASET_NAME>/`（名称未定，改这一处即全局生效）。

mmaction2 两种视频数据集类型（见 `mmaction/datasets/`）：
- **`VideoDataset`** —— 直接读原始视频文件；ann_file 是 txt，每行 `相对路径 标签`：
  ```
  train/abroll_cat_001.mp4 0
  train/walk_dog_002.mp4 1
  ```
  config: `data_root='datasets/<NAME>/videos_train'`, `ann_file_train='datasets/<NAME>/<NAME>_train_list.txt'`。
- **`RawframeDataset`** —— 读已抽帧的图片目录；ann_file 每行 `帧目录路径 起始帧 标签 总帧数`。视频多时先用 VideoDataset。

**写一个我们的数据集 base config**（放 `evaluation/configs/dataset_quadruped.py` 或 `models/mmaction2/configs/_base_/datasets/`，按项目归属见 §6）：

```python
# _base_/datasets/quadruped.py —— 由 server/config.py 的 QUADRUPED_DATASET_NAME 解析后注入
dataset_type = 'VideoDataset'
data_root = 'datasets/quadruped_action/videos_train/'     # ← 与 QUADRUPED_DATASET_NAME 一致
data_root_val = 'datasets/quadruped_action/videos_val/'
ann_file_train = 'datasets/quadruped_action/quadruped_action_train_list.txt'
ann_file_val = 'datasets/quadruped_action/quadruped_action_val_list.txt'
num_classes = <待数据集类别确定后填>           # 与 cls_head.num_classes 同步
train_pipeline = [...]   # 复用 kinetics 的 pipeline，按需调 input_size / num_clips
val_pipeline = [...]
test_pipeline = [...]
```

> 数据尚未收集时 `num_samples=0`（已在 `training.py` DEFAULT_DATASETS 标 `status: pending_collection`）；数据到位后只需：放视频 + 生成 train/val txt 列表 + 填 `num_classes`。

## 5. 与我们训练框架对接

`server/routers/training.py`（pet-action 下游版，覆盖上游脚手架）契约：

| 端点 | 用途 | 与 mmaction2 的关系 |
|------|------|----------------------|
| `GET /api/training/models` | 可训练模型清单 | step 3 注册每个 mmaction2 模型族 → `DEFAULT_MODELS`/registry |
| `GET /api/training/datasets` | 数据集清单 | 四足数据集（`QUADRUPED_DATASET_NAME`） |
| `GET /api/training/configs` | 超参 preset | epochs/lr/optimizer/scheduler |
| `POST /api/training/run` | 触发训练 | **下游实接**：subprocess `tools/train.py`，见下 |
| `GET /api/training/runs` | run 列表 | 读 `results/training/metrics.json` |
| `GET /api/training/outputs/{path}` | 下载 checkpoint/log | 服务 `results/training/` |

`POST /run` 实接要点（step 3 完成）：
```python
# 伪码
run_id = f"train-{int(time.time())}"
cmd = ["python", "models/mmaction2/tools/train.py",
       cfg_path, "--work-dir", f"results/training/runs/{run_id}"]
# 子进程异步跑；跑完：
#   - 把最新 epoch_*.pth 软链/拷到 results/training/checkpoints/{run_id}.pth
#   - 解析 vis_data/scalars.json → loss_series
#   - 追加一条 run 到 results/training/metrics.json
```

`metrics.json` shape（`{generated_at, runs: [...]}`，单 run）：
```json
{
  "id": "train-...",
  "model": "tsn-resnet50",
  "dataset": "quadruped_action",
  "status": "completed",
  "metrics": {"top1_acc": 0.82, "top5_acc": 0.97},
  "loss_series": [[0, 4.2], [1, 3.1], ...],
  "checkpoint_path": "checkpoints/train-....pth"
}
```
web 训练结果页（`web/src/views/training/TrainResults.vue`）读这个 json 画 loss 曲线 + 列 run —— 已由上游脚手架接好，无需改前端。

## 6. 责任归属（改 mmaction2 源码 vs 写 config）

- **改 `models/mmaction2/**` 源码** —— 慎用。vendor 的库升级会冲掉本地改动。优先用 config 覆盖（`model=dict(...)`）、`custom_imports`、或在我们 `evaluation/` 里写子类。
- **我们自己的 config / dataset base / registry** —— 放 `evaluation/configs/` 与 `evaluation/models/`（领域代码，下游自管，不进上游、不进 models）。
- 共享脚手架改动（如修 `file_utils.py`）→ 走 [[upstream-sync]] 工作流，先 port 回 ProjFlow。

## 7. mmaction2 模型族 → 训练 registry 映射（step 3 用）

`configs/recognition/` 下的模型族（每个族挑一个代表 config 注册）：

| 族 | 代表 config 目录 | base model | 类型 |
|----|------------------|------------|------|
| TSN | `configs/recognition/tsn/` | `_base_/models/tsn_r50.py` | 2D CNN 帧采样 |
| TSM | `configs/recognition/tsm/` | `tsm_r50.py` | 2D CNN + 位移 |
| I3D | `configs/recognition/i3d/` | `i3d_r50.py` | 3D CNN |
| C3D | `configs/recognition/c3d/` | `c3d_sports1m_pretrained.py` | 3D CNN |
| SlowFast | `configs/recognition/slowfast/` | `slowfast_r50.py` | 双路径 3D CNN |
| SlowOnly | `configs/recognition/slowonly/` | `slowonly_r50.py` | 单路径 |
| R(2+1)D | `configs/recognition/r2plus1d/` | `r2plus1d_r34.py` | 2.5D CNN |
| CSN | `configs/recognition/csn/` | `ircsn_r152.py` | 3D CNN |
| TIN | `configs/recognition/tin/` | `tin_r50.py` | 帧插值 |
| TRN | `configs/recognition/trn/` | `trn_r50.py` | 关系推理 |
| TPN | `configs/recognition/tpn/` | `tpn_*.py` | 时序金字塔 |
| Tanet | `configs/recognition/tanet/` | `tanet_r50.py` | 时空注意力 |
| TimeSformer | `configs/recognition/timesformer/` | — | ViT 视频 |
| MViT | `configs/recognition/mvit/` | `mvit_small.py` | ViT 视频 |
| Swin | `configs/recognition/swin/` | `swin_tiny.py` | 视频 Swin |
| X3D | `configs/recognition/x3d/` | `x3d.py` | 轻量 3D |
| Uniformer | `configs/recognition/uniformer/` | — | 统一 Transformer |
| VideoMAE | `configs/recognition/videomae/` | — | MAE 预训练 |
| VideoMAEv2 | `configs/recognition/videomaev2/` | — | MAEv2 |

> **不在 mmaction2 的模型**（README 提到但属外部库，需单独集成，非本 skill 范围）：VideoMamba、SkeleTR、PMTNet、InternVideo2。`projects/` 下另有贡献配方（actionclip/ctrgcn/msg3d/umt 等），可选。

## 8. 常见坑

- `num_classes` 不匹配 → `cls_head=dict(num_classes=N)` 覆盖，N = 四足数据集类别数。
- `decord` 报错 → 换 `AVInit`/PyAV，或改 `RawframeDataset` 预抽帧。
- mmcv 版本 → mmaction2 要求 `mmcv>=2.0.0`（非 mmcv-full），用 `mim install` 锁版本。
- checkpoint 路径穿越 → `server/routers/training.py` 的 `/outputs` 端点用 `safe_resolve` 守卫（已在 `server/utils/file_utils.py`）。
- 训练 OOM → 调小 `batch_size`、加 `--amp`、降 `clip_len`/`num_clips`。
