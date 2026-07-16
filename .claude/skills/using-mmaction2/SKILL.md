---
name: using-mmaction2
description: |
  在 pet-action-recognition 训练框架下使用 mmaction2 的指南。说明 mmaction2 的安装、config 系统（_base_ 继承）、训练入口（tools/train.py）、如何把数据集与模型适配到我们的训练 registry，以及与 server/routers/training.py + results/training/ + web 训练页的对接。
  触发场景：(1) 训练/调用 mmaction2 模型 (2) 把新模型族注册进训练 registry (3) 适配四足动物数据集到 mmaction2 (4) 排查 mmaction2 训练报错 (5) 升级 third_party/mmaction2 vendor
---

# 在本仓库使用 mmaction2

mmaction2 = OpenMMLab 视频动作识别库。**已 vendor 进仓库**：`third_party/mmaction2/`（shallow clone，HEAD `a5a167d`，见 `third_party/README.md`）。不是 pip 依赖、不是 submodule —— 文件直接在本仓库历史里。

## 1. 安装

mmaction2 依赖 mmengine + mmcv + torch + decord。推荐 editable 安装 vendor 目录：

```bash
# 1) 先装 torch（按本机 CUDA / CPU 自选），再：
pip install -U openmim
mim install mmengine "mmcv>=2.0.0"
pip install decord einops opencv-contrib-python scipy matplotlib
# 2) editable 装 vendor 的 mmaction2（改 third_party/mmaction2 源码即时生效）
pip install -v -e third_party/mmaction2
# 3) 验证
python -c "import mmaction; print(mmaction.__version__)"
```

> 若 decord 装不上（macOS / 老 Python），可用 PyAV 后端或 `pip install av`，config 里把 `DecordInit` 换 `AVInit`。训练时报 `No module named 'mmcv'` → `mim install mmcv`；报 `MMCV_WITH_OPS=0` → 装 prebuilt mmcv（`mim install mmcv-full` 对老版本，2.x 用 `mmcv`）。

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

## 3. 训练入口

```bash
python third_party/mmaction2/tools/train.py <CONFIG.py> \
    --work-dir results/training/runs/<run_id> \
    [--resume] [--amp] [--seed 42]
# 多卡：
bash third_party/mmaction2/tools/dist_train.sh <CONFIG> <NGPU> --work-dir ...
```

产物（写到 `--work-dir`）：`<run_id>/epoch_*.pth`（checkpoint）、`<run_id>/*.log` + `vis_data/scalars.json`（loss/metric 曲线）。我们要把这些搬到 `results/training/checkpoints/` 与 `results/training/logs/` 并汇总进 `metrics.json`（见 §5）。

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

**写一个我们的数据集 base config**（放 `evaluation/configs/dataset_quadruped.py` 或 `third_party/mmaction2/configs/_base_/datasets/`，按项目归属见 §6）：

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
cmd = ["python", "third_party/mmaction2/tools/train.py",
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

- **改 `third_party/mmaction2/**` 源码** —— 慎用。vendor 的库升级会冲掉本地改动。优先用 config 覆盖（`model=dict(...)`）、`custom_imports`、或在我们 `evaluation/` 里写子类。
- **我们自己的 config / dataset base / registry** —— 放 `evaluation/configs/` 与 `evaluation/models/`（领域代码，下游自管，不进上游、不进 third_party）。
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
