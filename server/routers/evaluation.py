"""评测体系路由"""
import os
import json
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse
from server.config import EVALUATION_DIR, OUTPUTS_DIR
from server.utils.file_utils import read_file, scan_directory, safe_resolve

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

# 视频文件扩展名 -> MIME（outputs 端点按需服务压缩码流/重建视频）
VIDEO_MIME = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".m4v": "video/x-m4v",
}

# 默认模型数据（当 evaluation/models/ 为空时使用）
DEFAULT_MODELS = [
    {'id': 'slowfast', 'name': 'SlowFast', 'type': '3D CNN 双路径', 'params': '34M', 'description': '粗粒度基线'},
    {'id': 'i3d', 'name': 'I3D', 'type': '3D CNN', 'params': '12M', 'description': '经典基线'},
    {'id': 'videomamba', 'name': 'VideoMamba', 'type': 'SSM', 'params': '74M', 'description': '边缘部署候选'},
    {'id': 'skeletr', 'name': 'SkeleTR', 'type': '骨架 Transformer', 'params': '-', 'description': '细粒度识别'},
    {'id': 'pmtnet', 'name': 'PMTNet', 'type': '部件级时序', 'params': '-', 'description': '猫行为专用（93.1%）'},
    {'id': 'internvideo2', 'name': 'InternVideo2', 'type': 'VFM', 'params': '6B', 'description': 'SOTA'},
]

# 默认数据集数据
DEFAULT_DATASETS = [
    {'id': 'animal_kingdom', 'name': 'Animal Kingdom', 'num_classes': 140, 'num_samples': '33K', 'modalities': ['RGB'], 'description': 'CVPR 2022 动物行为数据集'},
    {'id': 'mammalnet', 'name': 'MammalNet', 'num_classes': 30, 'num_samples': '190K', 'modalities': ['RGB'], 'description': '哺乳动物行为识别'},
    {'id': 'cvb', 'name': 'CVB', 'num_classes': 12, 'num_samples': '9K', 'modalities': ['RGB'], 'description': '猫视频行为数据集'},
    {'id': 'pbrd', 'name': 'PBRD', 'num_classes': 8, 'num_samples': '-', 'modalities': ['RGB'], 'description': '宠物行为识别数据集'},
]


@router.get("/models")
async def get_models():
    """获取模型列表"""
    models = _load_from_dir(os.path.join(EVALUATION_DIR, 'models'), 'models.json')
    return models if models else DEFAULT_MODELS


@router.get("/models/{model_id}")
async def get_model_detail(model_id: str):
    """获取模型详情"""
    models = await get_models()
    for m in models:
        if m.get('id') == model_id:
            return m
    return {'detail': 'Model not found'}, 404


@router.get("/datasets")
async def get_datasets():
    """获取数据集列表"""
    datasets = _load_from_dir(os.path.join(EVALUATION_DIR, 'datasets'), 'datasets.json')
    return datasets if datasets else DEFAULT_DATASETS


@router.get("/datasets/{dataset_id}")
async def get_dataset_detail(dataset_id: str):
    """获取数据集详情"""
    datasets = await get_datasets()
    for d in datasets:
        if d.get('id') == dataset_id:
            return d
    return {'detail': 'Dataset not found'}, 404


@router.get("/configs")
async def get_configs():
    """获取评测配置列表"""
    configs = _load_from_dir(os.path.join(EVALUATION_DIR, 'configs'), 'configs.json')
    return configs if configs else []


@router.get("/configs/{config_id}")
async def get_config_detail(config_id: str):
    """获取指定评测配置"""
    configs = await get_configs()
    for c in configs:
        if c.get('id') == config_id:
            return c
    return {'detail': 'Config not found'}, 404


@router.post("/run")
async def run_evaluation(data: dict = Body(...)):
    """启动评测任务。

    契约返回 ``output_video``（相对 OUTPUTS_DIR 的路径或 None）——下游若实际执行
    评测脚本，应填真实输出码流路径，前端据此按需展示输出视频+指标。
    """
    return {
        'status': 'pending',
        'message': '评测任务已提交',
        'config': data,
        'output_video': None,
        'metrics': None,
        'note': '上游脚手架为模拟响应；下游库（如 infraredComp）实接评测脚本后填充 output_video/metrics。',
    }


# ---- 输出视频/码流（按需服务，防路径穿越）--------------------------- #

@router.get("/outputs")
async def list_outputs():
    """列出 OUTPUTS_DIR 下可查看的输出文件（视频/码流），供 EvalOutputs 浏览。"""
    if not os.path.isdir(OUTPUTS_DIR):
        return {"outputs": []}
    out = []
    for root, _, files in os.walk(OUTPUTS_DIR):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, OUTPUTS_DIR)
            ext = os.path.splitext(fn)[1].lower()
            out.append({
                "name": fn,
                "path": rel.replace(os.sep, "/"),
                "ext": ext,
                "is_video": ext in VIDEO_MIME,
                "size_bytes": os.path.getsize(full),
            })
    out.sort(key=lambda x: x["path"])
    return {"outputs": out}


@router.get("/outputs/{file_path:path}")
async def serve_output(file_path: str):
    """按需服务一个输出文件（视频码流/重建帧），流式 FileResponse。

    路径经 safe_resolve 校验必须位于 OUTPUTS_DIR 内，防穿越。
    前端 <video preload="none"> 仅在用户点开后才请求此端点。
    """
    safe = safe_resolve(OUTPUTS_DIR, file_path)
    if not safe or not os.path.isfile(safe):
        return {"detail": "Output not found"}, 404
    ext = os.path.splitext(safe)[1].lower()
    media = VIDEO_MIME.get(ext, "application/octet-stream")
    return FileResponse(safe, media_type=media, filename=os.path.basename(safe))


@router.get("/results")
async def get_results(model: str = None, dataset: str = None, metric: str = None):
    """获取评测结果列表"""
    results = _load_from_dir(os.path.join(EVALUATION_DIR, 'results'), 'results.json')

    if model:
        results = [r for r in results if r.get('model_name') == model]
    if dataset:
        results = [r for r in results if r.get('dataset_name') == dataset]

    return results if results else []


@router.get("/results/compare")
async def compare_results(models: str = None, datasets: str = None):
    """获取对比结果"""
    results = _load_from_dir(os.path.join(EVALUATION_DIR, 'results'), 'results.json')
    if not results:
        return []

    model_list = models.split(',') if models else None
    dataset_list = datasets.split(',') if datasets else None

    filtered = results
    if model_list:
        filtered = [r for r in filtered if r.get('model_name') in model_list]
    if dataset_list:
        filtered = [r for r in filtered if r.get('dataset_name') in dataset_list]

    return filtered


@router.get("/results/{result_id}")
async def get_result_detail(result_id: str):
    """获取单条评测结果详情"""
    results = _load_from_dir(os.path.join(EVALUATION_DIR, 'results'), 'results.json')
    for r in results:
        if r.get('id') == result_id:
            return r
    return {'detail': 'Result not found'}, 404


def _load_from_dir(dir_path, json_filename):
    """从目录加载 JSON 数据"""
    if not os.path.exists(dir_path):
        return []

    json_file = os.path.join(dir_path, json_filename)
    content = read_file(json_file)
    if content:
        try:
            data = json.loads(content)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            pass

    results = []
    for f in scan_directory(dir_path, pattern=r'.*\.json$'):
        content = read_file(f)
        if content:
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.append(data)
            except json.JSONDecodeError:
                pass

    return results
