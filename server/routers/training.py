"""训练体系路由 — pet-action-recognition 下游版（mmaction2 实接）。

领域接线：
  - 模型：mmaction2 模型族（TSN/TSM/I3D/C3D/SlowFast/...），vendor 在 third_party/mmaction2/。
  - 数据集：四足动物动作数据集（QUADRUPED_DATASET_NAME）。
  - 训练脚本：POST /run subprocess 调用 scripts/train_model.py，后者包装
    third_party/mmaction2/tools/train.py，写入 results/training/metrics.json。
  - 测试脚本：POST /run_test subprocess 调用 scripts/run_test.py，包装
    third_party/mmaction2/tools/test.py，写入 results/training/test_results.json。
  - 推理脚本：POST /inference subprocess 调用 scripts/inference.py，支持单视频。
"""
from __future__ import annotations

import os
import json
import subprocess
import sys
import time

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse

from server.config import (
    TRAINING_METRICS_JSON, TRAINING_TEST_RESULTS_JSON, CHECKPOINTS_DIR, TRAINING_OUTPUTS_DIR,
    TRAINING_DIR, TRAINING_WORK_DIR, MMACTION2_DIR,
    QUADRUPED_DATASET_NAME, QUADRUPED_DATASET_DIR, QUADRUPED_CLASSES_FILE,
)
from server.utils.file_utils import read_file, safe_resolve

router = APIRouter(prefix="/api/training", tags=["training"])

TRAIN_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "train_model.py")
TEST_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "run_test.py")
INFER_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "inference.py")
INFERENCE_DIR = os.path.join(TRAINING_DIR, "inference")

# mmaction2 训练 registry：每个族挑一个代表 config（相对 MMACTION2_DIR）
_MMACTION2_REGISTRY = [
    {
        "id": "tsn-resnet50",
        "name": "TSN (ResNet-50)",
        "family": "TSN",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb_20220906-cd10898e.pth",
        "mmaction2_config": "configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py",
        "description": "2D CNN 帧采样基线；mmaction2 代表实现。",
    },
    {
        "id": "tsm-resnet50",
        "name": "TSM (ResNet-50)",
        "family": "TSM",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tsm/tsm_imagenet-pretrained-r50_8xb16-1x1x8-100e_kinetics400-rgb/tsm_imagenet-pretrained-r50_8xb16-1x1x8-100e_kinetics400-rgb_20220831-a6db1e5d.pth",
        "mmaction2_config": "configs/recognition/tsm/tsm_imagenet-pretrained-r50_8xb16-1x1x8-100e_kinetics400-rgb.py",
        "description": "2D CNN + 时序位移模块，轻量高效。",
    },
    {
        "id": "i3d-resnet50",
        "name": "I3D (ResNet-50)",
        "family": "I3D",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/i3d/i3d_imagenet-pretrained-r50_8xb8-32x2x1-100e_kinetics400-rgb/i3d_imagenet-pretrained-r50_8xb8-32x2x1-100e_kinetics400-rgb_20220812-e213c223.pth",
        "mmaction2_config": "configs/recognition/i3d/i3d_imagenet-pretrained-r50_8xb8-32x2x1-100e_kinetics400-rgb.py",
        "description": "经典 3D CNN 膨胀卷积基线。",
    },
    {
        "id": "c3d-sports1m",
        "name": "C3D (Sports-1M pretrain)",
        "family": "C3D",
        "backbone": "c3d",
        "pretrained_source": "UCF-101 (from Sports-1M)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/c3d/c3d_sports1m-pretrained_8xb30-16x1x1-45e_ucf101-rgb/c3d_sports1m-pretrained_8xb30-16x1x1-45e_ucf101-rgb_20220811-31723200.pth",
        "mmaction2_config": "configs/recognition/c3d/c3d_sports1m-pretrained_8xb30-16x1x1-45e_ucf101-rgb.py",
        "description": "早期 3D CNN 代表，Sports-1M 预训练。",
    },
    {
        "id": "slowfast-resnet50",
        "name": "SlowFast (ResNet-50)",
        "family": "SlowFast",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/slowfast/slowfast_r50_8xb8-4x16x1-256e_kinetics400-rgb/slowfast_r50_8xb8-4x16x1-256e_kinetics400-rgb_20220901-701b0f6f.pth",
        "mmaction2_config": "configs/recognition/slowfast/slowfast_r50_8xb8-4x16x1-256e_kinetics400-rgb.py",
        "description": "3D CNN 双路径（慢/快）。",
    },
    {
        "id": "slowonly-resnet50",
        "name": "SlowOnly (ResNet-50)",
        "family": "SlowOnly",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-700",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/slowonly/slowonly_imagenet-pretrained-r50_16xb16-4x16x1-steplr-150e_kinetics700-rgb/slowonly_imagenet-pretrained-r50_16xb16-4x16x1-steplr-150e_kinetics700-rgb_20221013-98b1b0a7.pth",
        "mmaction2_config": "configs/recognition/slowonly/slowonly_imagenet-pretrained-r50_16xb16-4x16x1-steplr-150e_kinetics700-rgb.py",
        "description": "SlowFast 的慢路径单分支版本。",
    },
    {
        "id": "r2plus1d-resnet34",
        "name": "R(2+1)D (ResNet-34)",
        "family": "R(2+1)D",
        "backbone": "resnet34",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/r2plus1d/r2plus1d_r34_8xb8-8x8x1-180e_kinetics400-rgb/r2plus1d_r34_8xb8-8x8x1-180e_kinetics400-rgb_20220812-47cfe041.pth",
        "mmaction2_config": "configs/recognition/r2plus1d/r2plus1d_r34_8xb8-8x8x1-180e_kinetics400-rgb.py",
        "description": "2.5D CNN 基线。",
    },
    {
        "id": "csn-ircsn152",
        "name": "CSN / irCSN-152",
        "family": "CSN",
        "backbone": "resnet152",
        "pretrained_source": "Kinetics-400 (from IG-65M)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/csn/ircsn_ig65m-pretrained-r152_8xb12-32x2x1-58e_kinetics400-rgb/ircsn_ig65m-pretrained-r152_8xb12-32x2x1-58e_kinetics400-rgb_20220811-c7a3cc5b.pth",
        "mmaction2_config": "configs/recognition/csn/ircsn_ig65m-pretrained-r152_8xb12-32x2x1-58e_kinetics400-rgb.py",
        "description": "Channel-Separated 3D CNN。",
    },
    {
        "id": "tin-resnet50",
        "name": "TIN (ResNet-50)",
        "family": "TIN",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400 (from TSM)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tin/tin_kinetics400-pretrained-tsm-r50_1x1x8-50e_kinetics400-rgb/tin_kinetics400-pretrained-tsm-r50_1x1x8-50e_kinetics400-rgb_20220913-7f10d0c0.pth",
        "mmaction2_config": "configs/recognition/tin/tin_kinetics400-pretrained-tsm-r50_1x1x8-50e_kinetics400-rgb.py",
        "description": "Temporal Interlacing Network。",
    },
    {
        "id": "trn-resnet50",
        "name": "TRN (ResNet-50)",
        "family": "TRN",
        "backbone": "resnet50",
        "pretrained_source": "Something-Something V2",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/trn/trn_imagenet-pretrained-r50_8xb16-1x1x8-50e_sthv2-rgb/trn_imagenet-pretrained-r50_8xb16-1x1x8-50e_sthv2-rgb_20220815-e01617db.pth",
        "mmaction2_config": "configs/recognition/trn/trn_imagenet-pretrained-r50_8xb16-1x1x8-50e_sthv2-rgb.py",
        "description": "Temporal Relation Network。",
    },
    {
        "id": "tpn-slowonly-r50",
        "name": "TPN + SlowOnly (ResNet-50)",
        "family": "TPN",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tpn/tpn_imagenet_pretrained_slowonly_r50_8x8x1_150e_kinetics_rgb/tpn-slowonly_imagenet-pretrained-r50_8xb8-8x8x1-150e_kinetics400-rgb_20220913-fed3f4c1.pth",
        "mmaction2_config": "configs/recognition/tpn/tpn-slowonly_imagenet-pretrained-r50_8xb8-8x8x1-150e_kinetics400-rgb.py",
        "description": "Temporal Pyramid Network。",
    },
    {
        "id": "tanet-resnet50",
        "name": "TANet (ResNet-50)",
        "family": "TANet",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tanet/tanet_imagenet-pretrained-r50_8xb8-dense-1x1x8-100e_kinetics400-rgb/tanet_imagenet-pretrained-r50_8xb8-dense-1x1x8-100e_kinetics400-rgb_20220919-a34346bc.pth",
        "mmaction2_config": "configs/recognition/tanet/tanet_imagenet-pretrained-r50_8xb8-dense-1x1x8-100e_kinetics400-rgb.py",
        "description": "Temporal Adaptive Network。",
    },
    {
        "id": "timesformer-divst",
        "name": "TimeSformer (divST)",
        "family": "TimeSformer",
        "backbone": "vit_base",
        "pretrained_source": "Kinetics-400 (from IN-21K ViT)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/timesformer/timesformer_divST_8xb8-8x32x1-15e_kinetics400-rgb/timesformer_divST_8xb8-8x32x1-15e_kinetics400-rgb_20220815-a4d0d01f.pth",
        "mmaction2_config": "configs/recognition/timesformer/timesformer_divST_8xb8-8x32x1-15e_kinetics400-rgb.py",
        "description": "纯 ViT 视频 Transformer。",
    },
    {
        "id": "mvit-small",
        "name": "MViT (Small)",
        "family": "MViT",
        "backbone": "mvit",
        "pretrained_source": "Kinetics-400",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/mvit/mvit-small-p244_32xb16-16x4x1-200e_kinetics400-rgb/mvit-small-p244_32xb16-16x4x1-200e_kinetics400-rgb_20230201-23284ff3.pth",
        "mmaction2_config": "configs/recognition/mvit/mvit-small-p244_32xb16-16x4x1-200e_kinetics400-rgb.py",
        "description": "Multiscale Vision Transformer。",
    },
    {
        "id": "swin-tiny",
        "name": "Swin-Base (K400)",
        "family": "Swin",
        "backbone": "swin_base",
        "pretrained_source": "Kinetics-400 (from IN-1K Swin-B)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/swin/swin-base-p244-w877_in1k-pre_8xb8-amp-32x2x1-30e_kinetics400-rgb/swin-base-p244-w877_in1k-pre_8xb8-amp-32x2x1-30e_kinetics400-rgb_20220930-182ec6cc.pth",
        "mmaction2_config": "configs/recognition/swin/swin-base-p244-w877_in1k-pre_8xb8-amp-32x2x1-30e_kinetics400-rgb.py",
        "description": "视频 Swin Transformer。",
    },
    {
        "id": "x3d-xs",
        "name": "X3D (S)",
        "family": "X3D",
        "backbone": "x3d",
        "pretrained_source": "Kinetics-400 (Facebook)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/x3d/facebook/x3d_s_13x6x1_facebook-kinetics400-rgb_20201027-623825a0.pth",
        "mmaction2_config": "configs/recognition/x3d/x3d_s_13x6x1_facebook-kinetics400-rgb.py",
        "description": "轻量 3D CNN，适合移动端。",
    },
    {
        "id": "uniformer-base",
        "name": "UniFormer (Base)",
        "family": "UniFormer",
        "backbone": "uniformer",
        "pretrained_source": "Kinetics-400 (from IN-1K)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/uniformerv1/uniformer-base_imagenet1k-pre_16x4x1_kinetics400-rgb_20221219-157c2e66.pth",
        "mmaction2_config": "configs/recognition/uniformer/uniformer-base_imagenet1k-pre_16x4x1_kinetics400-rgb.py",
        "description": "统一卷积+Transformer 视频模型。",
    },
    {
        "id": "videomae-base",
        "name": "VideoMAE (Base)",
        "family": "VideoMAE",
        "backbone": "vit_base",
        "pretrained_source": "Kinetics-400 (MAE self-supervised)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/videomae/vit-base-p16_videomae-k400-pre_16x4x1_kinetics-400_20221013-860a3cd3.pth",
        "mmaction2_config": "configs/recognition/videomae/vit-base-p16_videomae-k400-pre_16x4x1_kinetics-400.py",
        "description": "MAE 自监督视频 Transformer。",
    },
    {
        "id": "videomaev2-base",
        "name": "VideoMAEv2 (Base)",
        "family": "VideoMAEv2",
        "backbone": "vit_base",
        "pretrained_source": "Kinetics-400 (distilled from ViT-G K710)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/videomaev2/vit-base-p16_videomaev2-vit-g-dist-k710-pre_16x4x1_kinetics-400/vit-base-p16_videomaev2-vit-g-dist-k710-pre_16x4x1_kinetics-400_20230510-3e7f93b2.pth",
        "mmaction2_config": "configs/recognition/videomaev2/vit-base-p16_videomaev2-vit-g-dist-k710-pre_16x4x1_kinetics-400.py",
        "description": "VideoMAE 第二代。",
    },
    {
        "id": "c2d-resnet50",
        "name": "C2D (ResNet-50)",
        "family": "C2D",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400 (from IN-1K)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/c2d/c2d_r50-in1k-pre_8xb32-8x8x1-100e_kinetics400-rgb/c2d_r50-in1k-pre_8xb32-8x8x1-100e_kinetics400-rgb_20221027-3ca304fa.pth",
        "mmaction2_config": "configs/recognition/c2d/c2d_r50-in1k-pre_8xb32-8x8x1-100e_kinetics400-rgb.py",
        "description": "2D 卷积视频基线。",
    },
    {
        "id": "tsn-resnet50-quadruped",
        "name": "TSN (ResNet-50) — 四足动作本地配置",
        "family": "TSN",
        "backbone": "resnet50",
        "pretrained_source": "Kinetics-400 (via tsn-resnet50)",
        "pretrained_url": "https://download.openmmlab.com/mmaction/v1.0/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb_20220906-cd10898e.pth",
        "mmaction2_config": "/Users/tangwen/pet-action-recognition/evaluation/configs/quadruped_tsn_r50.py",
        "description": "小分辨率、PyAV 后端；可加载 TSN K400 预训练权重做 finetune。",
    },
]

# 数据集 shape: {id, name, splits, num_samples, modalities, status, description}
_has_dataset = (
    os.path.isdir(QUADRUPED_DATASET_DIR)
    and os.path.isfile(os.path.join(QUADRUPED_DATASET_DIR, f"{QUADRUPED_DATASET_NAME}_train_list.txt"))
)

DEFAULT_DATASETS = [
    {
        "id": QUADRUPED_DATASET_NAME,
        "name": "四足动物动作数据集",
        "splits": ["train", "val", "test"],
        "num_samples": 0,
        "modalities": ["rgb"],
        "status": "collected" if _has_dataset else "pending_collection",
        "root_dir": QUADRUPED_DATASET_DIR,
        "description": "猫/狗等四足动物动作识别数据集；名称未定，见 server/config.py QUADRUPED_DATASET_NAME（改一处即全局生效）。",
    },
]

# 动作识别超参 preset
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
    {
        "id": "fast",
        "name": "快速验证",
        "epochs": 5,
        "lr": 1e-3,
        "batch_size": 4,
        "optimizer": "sgd",
        "scheduler": "none",
        "weight_decay": 1e-4,
        "momentum": 0.9,
        "freeze_backbone": False,
        "description": "5 epoch 小数据快速跑通 mmaction2 训练链路",
    },
]


def _load_metrics() -> dict:
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


def _save_metrics(data: dict) -> None:
    os.makedirs(os.path.dirname(TRAINING_METRICS_JSON), exist_ok=True)
    tmp = TRAINING_METRICS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TRAINING_METRICS_JSON)


def _upsert_run(run: dict) -> None:
    data = _load_metrics()
    runs = data.setdefault("runs", [])
    for i, r in enumerate(runs):
        if r.get("id") == run.get("id"):
            runs[i] = {**r, **run}
            break
    else:
        runs.append(run)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_metrics(data)


def _model_entry(m: dict) -> dict:
    m = dict(m)
    m["trained_checkpoints"] = _trained_checkpoints_for(m["id"])
    return m


def _read_json_meta(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _trained_checkpoints_for(model_id: str) -> dict:
    result = {"latest": [], "best": []}
    model_dir = os.path.join(CHECKPOINTS_DIR, model_id)
    if os.path.isdir(model_dir):
        for fn in sorted(os.listdir(model_dir)):
            if not fn.endswith(".json"):
                continue
            meta = _read_json_meta(os.path.join(model_dir, fn))
            if meta is None:
                continue
            ckpt_type = meta.get("type", "")
            if ckpt_type in ("latest", "best"):
                result[ckpt_type].append(meta)
    # legacy: root-level .pth without subdirectory
    if os.path.isdir(CHECKPOINTS_DIR):
        for fn in sorted(os.listdir(CHECKPOINTS_DIR)):
            if fn.startswith('.') or not fn.endswith('.pth'):
                continue
            if os.path.isdir(os.path.join(CHECKPOINTS_DIR, fn)):
                continue
            if model_id.replace('-', '_') in fn or model_id.replace('-', '') in fn or fn.startswith(f"{model_id}"):
                result["latest"].append({
                    "checkpoint_path": f"checkpoints/{fn}",
                    "type": "latest",
                    "legacy": True,
                })
    return result


def _model_config_path(model_id: str) -> str | None:
    for m in _MMACTION2_REGISTRY:
        if m["id"] == model_id:
            return m["mmaction2_config"]
    return None


def _num_classes() -> int | None:
    if not os.path.isfile(QUADRUPED_CLASSES_FILE):
        return None
    with open(QUADRUPED_CLASSES_FILE, "r", encoding="utf-8") as f:
        return len([ln.strip() for ln in f if ln.strip()])


# ---- models ------------------------------------------------------------- #

@router.get("/models")
async def get_models():
    """可训练模型清单（mmaction2 模型族）。"""
    return [_model_entry(m) for m in _MMACTION2_REGISTRY]


@router.get("/models/{model_id}")
async def get_model_detail(model_id: str):
    for m in await get_models():
        if m.get("id") == model_id:
            return m
    return {"detail": "Model not found"}, 404


# ---- datasets ---------------------------------------------------------- #

@router.get("/datasets")
async def get_datasets():
    """训练数据集清单。若目录已存在，动态更新 num_samples。"""
    out = []
    for d in DEFAULT_DATASETS:
        row = dict(d)
        if d["id"] == QUADRUPED_DATASET_NAME and os.path.isdir(QUADRUPED_DATASET_DIR):
            for split in ("train", "val", "test"):
                ann = os.path.join(QUADRUPED_DATASET_DIR, f"{QUADRUPED_DATASET_NAME}_{split}_list.txt")
                if os.path.isfile(ann):
                    with open(ann, "r", encoding="utf-8") as f:
                        row["num_samples"] = len([ln for ln in f if ln.strip()])
                    break
        out.append(row)
    return out


@router.get("/datasets/{dataset_id}")
async def get_dataset_detail(dataset_id: str):
    for d in await get_datasets():
        if d.get("id") == dataset_id:
            return d
    return {"detail": "Dataset not found"}, 404


# ---- configs ----------------------------------------------------------- #

@router.get("/configs")
async def get_configs():
    return DEFAULT_CONFIGS


@router.get("/configs/{config_id}")
async def get_config_detail(config_id: str):
    for c in DEFAULT_CONFIGS:
        if c.get("id") == config_id:
            return c
    return {"detail": "Config not found"}, 404


# ---- pretrained -------------------------------------------------------- #

def _pretrained_url_for(model_id: str) -> str | None:
    for m in _MMACTION2_REGISTRY:
        if m["id"] == model_id:
            return m.get("pretrained_url")
    return None


@router.get("/pretrained")
async def list_pretrained():
    """列出所有可用的预训练权重（来自 mmaction2 模型仓库）。"""
    out = []
    for m in _MMACTION2_REGISTRY:
        url = m.get("pretrained_url")
        if url:
            out.append({
                "model_id": m["id"],
                "model_name": m["name"],
                "family": m["family"],
                "source": m.get("pretrained_source", ""),
                "url": url,
            })
    return {"total": len(out), "pretrained": out}


# ---- run（触发训练）---------------------------------------------------- #

@router.post("/run")
async def run_training(data: dict = Body(...)):
    """异步触发 mmaction2 训练。

    四种训练模式互斥（只能选一个，都不选则使用 config 默认值）：
    - resume_from: 断点续训，复用 run_id，恢复 epoch/optimizer
    - load_from: 加载 checkpoint 权重，epoch=0 从头训练
    - pretrained: 加载 backbone 预训练权重（URL 或本地路径），finetune
    - from_scratch: 随机初始化，禁用 config 中的任何预训练权重
    """
    model_id = str(data.get("model_id", ""))
    dataset_id = str(data.get("dataset_id", QUADRUPED_DATASET_NAME))
    cfg_path = _model_config_path(model_id)
    if not cfg_path:
        return {"status": "error", "note": f"未知模型：{model_id}"}, 400

    resume_from = str(data.get("resume_from") or data.get("resume") or "").strip()
    load_from = str(data.get("load_from") or "").strip()
    pretrained_raw = data.get("pretrained")
    if pretrained_raw is True:
        pretrained = _pretrained_url_for(model_id) or ""
        if not pretrained:
            return {"status": "error", "note": f"模型 {model_id} 没有注册的预训练权重"}, 400
    else:
        pretrained = str(pretrained_raw or "").strip()
    from_scratch = bool(data.get("from_scratch"))

    active_modes = [
        n for n, v in [
            ("resume_from", resume_from),
            ("load_from", load_from),
            ("pretrained", pretrained),
            ("from_scratch", from_scratch or None),
        ] if v
    ]
    if len(active_modes) > 1:
        return {"status": "error", "note": f"训练模式互斥，只能选一个：{', '.join(active_modes)}"}, 400

    if resume_from:
        run_id = resume_from
        resume_path = os.path.join(CHECKPOINTS_DIR, model_id, f"{resume_from}_latest.pth")
        if os.path.isfile(resume_path):
            resume_path = os.path.realpath(resume_path)
        else:
            resume_path = "auto"
    else:
        run_id = f"train-{model_id}-{dataset_id}-{int(time.time())}"
        resume_path = None

    run = {
        "id": run_id,
        "model": model_id,
        "dataset": dataset_id,
        "status": "started",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epochs": data.get("epochs", 100),
        "lr": data.get("lr", 1e-3),
        "batch_size": data.get("batch_size", 16),
        "device": data.get("device", "cuda"),
        "checkpoint_path": None,
        "best_checkpoint_path": None,
    }
    if resume_from:
        run["resumed_at"] = run["started_at"]
    if load_from:
        run["loaded_from"] = load_from
    if pretrained:
        run["pretrained"] = pretrained
    if from_scratch:
        run["from_scratch"] = True
    _upsert_run(run)

    args = [
        sys.executable, TRAIN_SCRIPT,
        "--model-id", model_id,
        "--dataset-id", dataset_id,
        "--run-id", run_id,
        "--mmaction2-config", cfg_path,
        "--epochs", str(data.get("epochs", 100)),
        "--lr", str(data.get("lr", 1e-3)),
        "--batch-size", str(data.get("batch_size", 16)),
        "--device", str(data.get("device", "cuda")),
        "--seed", str(data.get("seed", 42)),
    ]
    n_cls = _num_classes()
    if n_cls is not None:
        args += ["--num-classes", str(n_cls)]
    if resume_path:
        args += ["--resume", resume_path]
    if load_from:
        args += [f"--load-from={load_from}"]
    if pretrained:
        args += [f"--pretrained={pretrained}"]
    if from_scratch:
        args += ["--from-scratch"]
    if data.get("extra_args"):
        args += [f"--extra-args={str(data['extra_args'])}"]

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(TRAIN_SCRIPT),
        )
        return {
            "status": "started",
            "run_id": run_id,
            "pid": proc.pid,
            "config": data,
            "checkpoint": None,
            "metrics": None,
            "note": "训练后台运行中；进度与 loss 曲线见 /api/training/runs。",
        }
    except FileNotFoundError as e:
        run["status"] = "error"
        run["error"] = str(e)
        _upsert_run(run)
        return {"status": "error", "run_id": run_id, "config": data, "note": f"训练脚本未找到: {TRAIN_SCRIPT}"}


# ---- run_test（触发测试/评估）------------------------------------------ #

@router.post("/run_test")
async def run_test(data: dict = Body(...)):
    """异步触发 mmaction2 测试（tools/test.py）。"""
    model_id = str(data.get("model_id", ""))
    checkpoint = str(data.get("checkpoint", ""))
    dataset_id = str(data.get("dataset_id", QUADRUPED_DATASET_NAME))
    split = str(data.get("split", "test"))
    cfg_path = _model_config_path(model_id)
    if not cfg_path:
        return {"status": "error", "note": f"未知模型：{model_id}"}, 400
    if not checkpoint:
        return {"status": "error", "note": "请提供 checkpoint 路径"}, 400

    run_id = f"test-{model_id}-{dataset_id}-{split}-{int(time.time())}"
    args = [
        sys.executable, TEST_SCRIPT,
        "--run-id", run_id,
        "--mmaction2-config", cfg_path,
        "--checkpoint", checkpoint,
        "--dataset-id", dataset_id,
        "--split", split,
        "--device", str(data.get("device", "cuda")),
    ]
    n_cls = _num_classes()
    if n_cls is not None:
        args += ["--num-classes", str(n_cls)]
    if data.get("extra_args"):
        # 使用 --key=value 形式，避免值以 '-' 开头时被 argparse 当成新选项
        args += [f"--extra-args={str(data['extra_args'])}"]

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(TEST_SCRIPT),
        )
        return {
            "status": "started",
            "run_id": run_id,
            "pid": proc.pid,
            "config": data,
            "note": "测试后台运行中；结果写入 results/training/test_results.json。",
        }
    except FileNotFoundError:
        return {"status": "error", "run_id": run_id, "note": f"测试脚本未找到: {TEST_SCRIPT}"}


@router.get("/test_results")
async def get_test_results():
    """测试/评估结果列表（读 test_results.json）。"""
    content = read_file(TRAINING_TEST_RESULTS_JSON)
    if not content:
        return {"generated_at": None, "results": []}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"generated_at": None, "results": [], "error": "Invalid test results JSON"}


# ---- inference（单视频推理）-------------------------------------------- #

@router.post("/inference")
async def run_inference(data: dict = Body(...)):
    """异步触发单视频推理。"""
    video = str(data.get("video", ""))
    checkpoint = str(data.get("checkpoint", ""))
    model_id = str(data.get("model_id", ""))
    if not video or not checkpoint or not model_id:
        return {"status": "error", "note": "请提供 video、checkpoint、model_id"}, 400
    cfg_path = _model_config_path(model_id)
    if not cfg_path:
        return {"status": "error", "note": f"未知模型：{model_id}"}, 400

    os.makedirs(INFERENCE_DIR, exist_ok=True)
    run_id = f"infer-{model_id}-{int(time.time())}"
    out_json = os.path.join(INFERENCE_DIR, f"{run_id}.json")
    args = [
        sys.executable, INFER_SCRIPT,
        "--video", video,
        "--checkpoint", checkpoint,
        "--mmaction2-config", cfg_path,
        "--device", str(data.get("device", "cuda:0")),
        "--output", out_json,
    ]
    if os.path.isfile(QUADRUPED_CLASSES_FILE):
        args += ["--labels", QUADRUPED_CLASSES_FILE]
    n_cls = _num_classes()
    if n_cls is not None:
        args += ["--num-classes", str(n_cls)]

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(INFER_SCRIPT),
        )
        return {
            "status": "started",
            "run_id": run_id,
            "pid": proc.pid,
            "output_path": f"inference/{run_id}.json",
            "note": "推理后台运行中；完成后 GET /api/training/inference/{run_id} 取结果。",
        }
    except FileNotFoundError:
        return {"status": "error", "run_id": run_id, "note": f"推理脚本未找到: {INFER_SCRIPT}"}


@router.get("/inference/{run_id}")
async def get_inference_result(run_id: str):
    path = os.path.join(INFERENCE_DIR, f"{run_id}.json")
    if not os.path.isfile(path):
        return {"detail": "Inference result not found or still running"}, 404
    content = read_file(path)
    if not content:
        return {"detail": "Empty inference result"}, 404
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"detail": "Invalid inference result JSON"}, 500


# ---- runs -------------------------------------------------------------- #

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


# ---- checkpoints ------------------------------------------------------- #

@router.get("/checkpoints")
async def list_checkpoints():
    """列出所有 checkpoint，优先读 JSON 元数据；对旧 .pth 降级。"""
    if not os.path.isdir(CHECKPOINTS_DIR):
        return {"checkpoints": []}
    out = []
    seen_paths = set()
    # model subdirectories
    for entry in sorted(os.listdir(CHECKPOINTS_DIR)):
        sub = os.path.join(CHECKPOINTS_DIR, entry)
        if not os.path.isdir(sub) or entry.startswith('.'):
            continue
        for fn in sorted(os.listdir(sub)):
            if not fn.endswith(".json"):
                continue
            meta = _read_json_meta(os.path.join(sub, fn))
            if meta is None:
                continue
            cp = meta.get("checkpoint_path", "")
            if cp:
                seen_paths.add(cp)
            # resolve actual file size
            pth_path = os.path.join(sub, fn.replace(".json", ".pth"))
            size = os.path.getsize(pth_path) if os.path.isfile(pth_path) else None
            out.append({
                **meta,
                "size_bytes": size,
            })
    # legacy root-level .pth
    for fn in sorted(os.listdir(CHECKPOINTS_DIR)):
        full = os.path.join(CHECKPOINTS_DIR, fn)
        if not os.path.isfile(full) or fn.startswith('.'):
            continue
        rel = f"checkpoints/{fn}"
        if rel in seen_paths:
            continue
        stem = os.path.splitext(fn)[0]
        out.append({
            "id": stem,
            "name": fn,
            "path": rel,
            "checkpoint_path": rel,
            "ext": os.path.splitext(fn)[1].lower(),
            "size_bytes": os.path.getsize(full),
            "legacy": True,
        })
    return {"checkpoints": out}


@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint_detail(checkpoint_id: str):
    """单 checkpoint 详情：优先读 JSON 元数据，再降级到 metrics.json runs 匹配。"""
    # 搜索模型子目录中的 JSON 元数据
    if os.path.isdir(CHECKPOINTS_DIR):
        for entry in os.listdir(CHECKPOINTS_DIR):
            sub = os.path.join(CHECKPOINTS_DIR, entry)
            if not os.path.isdir(sub):
                continue
            for fn in os.listdir(sub):
                stem = os.path.splitext(fn)[0]
                if stem == checkpoint_id and fn.endswith(".json"):
                    meta = _read_json_meta(os.path.join(sub, fn))
                    if meta:
                        return {"checkpoint": meta}
    # metrics.json runs 匹配
    data = _load_metrics()
    for r in data.get("runs", []):
        for key in ("checkpoint_path", "best_checkpoint_path"):
            cp = r.get(key, "")
            if cp and (checkpoint_id in cp or os.path.basename(cp) == checkpoint_id):
                return {"checkpoint": cp, "run": r}
    # 旧文件直接匹配
    if os.path.isdir(CHECKPOINTS_DIR):
        for entry in os.listdir(CHECKPOINTS_DIR):
            p = os.path.join(CHECKPOINTS_DIR, entry)
            if os.path.isfile(p):
                if os.path.splitext(entry)[0] == checkpoint_id:
                    return {"checkpoint": f"checkpoints/{entry}", "run": None}
            elif os.path.isdir(p):
                for fn in os.listdir(p):
                    if os.path.splitext(fn)[0] == checkpoint_id:
                        return {"checkpoint": f"checkpoints/{entry}/{fn}", "run": None}
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
    """按需服务一个训练产物文件（.pth checkpoint / .log 日志），流式 FileResponse。"""
    safe = safe_resolve(TRAINING_OUTPUTS_DIR, file_path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Output not found"}, 404
    ext = os.path.splitext(safe)[1].lower()
    media = {".pth": "application/octet-stream", ".log": "text/plain", ".json": "application/json"}.get(ext, "application/octet-stream")
    return FileResponse(safe, media_type=media, filename=os.path.basename(safe))
