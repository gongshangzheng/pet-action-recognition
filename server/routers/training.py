"""训练体系路由 — pet-action-recognition 下游版（覆盖上游脚手架）。

领域接线：
  - 模型：mmaction2 模型族（TSN/TSM/I3D/C3D/SlowFast/VideoMamba/TimeSformer/...），
    vendor 在 third_party/mmaction2/；完整 registry 见 step 3 填充。
  - 数据集：四足动物动作数据集（名称未定，变量 QUADRUPED_DATASET_NAME），位于
    datasets/<QUADRUPED_DATASET_NAME>/；数据尚未收集，先以骨架占位。
  - 训练脚本：POST /run 触发 mmaction2 训练入口（step 3 实接）。
  - metrics.json：训练 run 列表（含 loss_series），供 web 训练结果页展示。

数据目录（镜像 results/video/ 结构）：
  results/training/metrics.json     — 训练 run 列表(含 loss_series)
  results/training/checkpoints/     — trained .pth state_dicts
  results/training/logs/            — 训练日志
"""
import os
import json
import time

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse

from server.config import (
    TRAINING_METRICS_JSON, CHECKPOINTS_DIR, TRAINING_OUTPUTS_DIR,
    QUADRUPED_DATASET_NAME, QUADRUPED_DATASET_DIR,
)
from server.utils.file_utils import read_file, safe_resolve

router = APIRouter(prefix="/api/training", tags=["training"])

# ---- 领域默认数据（step 3 将由 registry 覆盖） ---------------------------- #
# 模型 shape: {id, name, family, backbone, pretrained_source, mmaction2_config,
#              trained_checkpoint?, description}
# step 1 仅放两条代表条目示范契约；step 3 按 mmaction2 模型族全量注册。
DEFAULT_MODELS = [
    {
        "id": "tsn-resnet50",
        "name": "TSN (ResNet-50)",
        "family": "TSN",
        "backbone": "resnet50",
        "pretrained_source": "mmaction2 torchvision",
        "mmaction2_config": "configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb",
        "trained_checkpoint": None,
        "description": "2D CNN 帧采样基线；mmaction2 代表实现，step 3 全量注册示范。",
    },
    {
        "id": "slowfast-resnet101",
        "name": "SlowFast (ResNet-101)",
        "family": "SlowFast",
        "backbone": "resnet101",
        "pretrained_source": "mmaction2",
        "mmaction2_config": "configs/recognition/slowfast/slowfast_resnet101_8xb32-4x16x1-256e_kinetics400-rgb",
        "trained_checkpoint": None,
        "description": "3D CNN 双路径；粗粒度基线代表。",
    },
]

# 数据集 shape: {id, name, splits, num_samples, modalities, status, description}
DEFAULT_DATASETS = [
    {
        "id": QUADRUPED_DATASET_NAME,
        "name": "四足动物动作数据集（名称待定）",
        "splits": ["train", "val", "test"],
        "num_samples": 0,            # 数据尚未收集，收集后更新
        "modalities": ["rgb"],
        "status": "pending_collection",
        "root_dir": QUADRUPED_DATASET_DIR,
        "description": "猫/狗等四足动物动作识别数据集；名称未定，见 server/config.py "
                       "QUADRUPED_DATASET_NAME 变量（改一处即全局生效）。",
    },
]

# 动作识别超参 preset（区别于上游 CompressAI 的 rate-distortion 超参）
DEFAULT_CONFIGS = [
    {
        "id": "default",
        "name": "默认训练配置",
        "epochs": 100,
        "lr": 1e-3,
        "batch_size": 16,
        "optimizer": "sgd",
        "scheduler": "cosine",
        "weight_decay": 1e-4,
        "momentum": 0.9,
        "freeze_backbone": False,
        "description": "动作识别默认超参 preset；按模型/数据集调",
    },
]


def _load_metrics() -> dict:
    """读 results/training/metrics.json。返回 {generated_at, runs: []}。"""
    content = read_file(TRAINING_METRICS_JSON)
    if not content:
        return {"generated_at": None, "runs": []}
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "runs" in data:
            return data
        return {"generated_at": None, "runs": data if isinstance(data, list) else []}
    except json.JSONDecodeError:
        return {"generated_at": None, "runs": []}


# ---- models（可训练 DL 模型）---------------------------------------------- #

@router.get("/models")
async def get_models():
    """可训练模型清单（mmaction2 模型族；step 3 全量注册）。"""
    return DEFAULT_MODELS


@router.get("/models/{model_id}")
async def get_model_detail(model_id: str):
    for m in DEFAULT_MODELS:
        if m.get("id") == model_id:
            return m
    return {"detail": "Model not found"}, 404


# ---- datasets（训练数据集）----------------------------------------------- #

@router.get("/datasets")
async def get_datasets():
    """训练数据集清单（四足动物动作数据集，名称见 QUADRUPED_DATASET_NAME）。"""
    return DEFAULT_DATASETS


@router.get("/datasets/{dataset_id}")
async def get_dataset_detail(dataset_id: str):
    for d in DEFAULT_DATASETS:
        if d.get("id") == dataset_id:
            return d
    return {"detail": "Dataset not found"}, 404


# ---- configs（超参 preset）----------------------------------------------- #

@router.get("/configs")
async def get_configs():
    """训练超参 preset（epochs/lr/batch/optimizer/scheduler；按模型/数据集增领域超参）。"""
    return DEFAULT_CONFIGS


@router.get("/configs/{config_id}")
async def get_config_detail(config_id: str):
    for c in DEFAULT_CONFIGS:
        if c.get("id") == config_id:
            return c
    return {"detail": "Config not found"}, 404


# ---- run（触发训练）------------------------------------------------------ #

@router.post("/run")
async def run_training(data: dict = Body(...)):
    """触发训练任务（异步）。契约返回 checkpoint（相对 TRAINING_OUTPUTS_DIR 的路径或 None）。

    下游实接：subprocess 触发训练脚本（如 scripts/train_model.py），训练完写
    metrics.json + checkpoints/{run_id}.pth + logs/{run_id}.log。
    """
    run_id = f"train-{int(time.time())}"
    return {
        "status": "pending",
        "run_id": run_id,
        "config": data,
        "checkpoint": None,
        "metrics": None,
        "note": "脚手架模拟响应；step 3 实接 mmaction2 训练入口后填充 checkpoint/metrics。",
    }


# ---- runs（训练 run 列表 + 详情）----------------------------------------- #

@router.get("/runs")
async def get_runs(model: str = None, dataset: str = None, status: str = None):
    """训练 run 列表（读 metrics.json）。可按 model/dataset/status 过滤。"""
    data = _load_metrics()
    runs = data.get("runs", [])
    if model:
        runs = [r for r in runs if r.get("model") == model]
    if dataset:
        runs = [r for r in runs if r.get("dataset") == dataset]
    if status:
        runs = [r for r in runs if r.get("status") == status]
    return {"generated_at": data.get("generated_at"), "total": len(runs), "runs": runs}


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str):
    """单条训练 run（含 loss_series）。"""
    data = _load_metrics()
    for r in data.get("runs", []):
        if r.get("id") == run_id:
            return r
    return {"detail": "Run not found"}, 404


# ---- checkpoints（trained .pth 文件）------------------------------------ #

@router.get("/checkpoints")
async def list_checkpoints():
    """列出 CHECKPOINTS_DIR 下的 trained checkpoint 文件。"""
    if not os.path.isdir(CHECKPOINTS_DIR):
        return {"checkpoints": []}
    out = []
    for fn in sorted(os.listdir(CHECKPOINTS_DIR)):
        full = os.path.join(CHECKPOINTS_DIR, fn)
        if not os.path.isfile(full) or fn.startswith('.'):
            continue
        stem = os.path.splitext(fn)[0]
        out.append({
            "id": stem,
            "name": fn,
            "path": f"checkpoints/{fn}",
            "ext": os.path.splitext(fn)[1].lower(),
            "size_bytes": os.path.getsize(full),
        })
    out.sort(key=lambda x: x["name"])
    return {"checkpoints": out}


@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint_detail(checkpoint_id: str):
    """单 checkpoint 详情（在 metrics.json runs 里找匹配 checkpoint_path）。"""
    data = _load_metrics()
    for r in data.get("runs", []):
        cp = r.get("checkpoint_path", "")
        if cp and (checkpoint_id in cp or os.path.basename(cp) == checkpoint_id):
            return {"checkpoint": cp, "run": r}
    # 兜底：直接看文件
    for fn in os.listdir(CHECKPOINTS_DIR) if os.path.isdir(CHECKPOINTS_DIR) else []:
        if os.path.splitext(fn)[0] == checkpoint_id:
            return {"checkpoint": f"checkpoints/{fn}", "run": None}
    return {"detail": "Checkpoint not found"}, 404


# ---- outputs（按需服务 checkpoint/log 文件，防穿越）---------------------- #

@router.get("/outputs")
async def list_outputs():
    """列出 TRAINING_OUTPUTS_DIR 下可下载/查看的文件（checkpoint + log）。"""
    if not os.path.isdir(TRAINING_OUTPUTS_DIR):
        return {"outputs": []}
    out = []
    for root, _, files in os.walk(TRAINING_OUTPUTS_DIR):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            if not os.path.isfile(full) or fn.startswith('.'):
                continue
            rel = os.path.relpath(full, TRAINING_OUTPUTS_DIR).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            out.append({
                "name": fn, "path": rel, "ext": ext,
                "size_bytes": os.path.getsize(full),
            })
    out.sort(key=lambda x: x["path"])
    return {"outputs": out}


@router.get("/outputs/{file_path:path}")
async def serve_output(file_path: str):
    """按需服务一个训练产物文件（.pth checkpoint / .log 日志），流式 FileResponse。

    路径经 safe_resolve 必须位于 TRAINING_OUTPUTS_DIR 内，防穿越。
    """
    safe = safe_resolve(TRAINING_OUTPUTS_DIR, file_path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Output not found"}, 404
    ext = os.path.splitext(safe)[1].lower()
    media = {".pth": "application/octet-stream", ".log": "text/plain", ".json": "application/json"}.get(ext, "application/octet-stream")
    return FileResponse(safe, media_type=media, filename=os.path.basename(safe))
