#!/usr/bin/env python3
"""mmaction2 单视频推理包装。

优先使用 mmaction2 的 Python API（init_recognizer + inference_recognizer）。
若环境未安装 mmaction2 依赖，则回退到生成临时 ann_file 调用 tools/test.py。

用法：
  python3 scripts/inference.py \
    --video /path/to/video.mp4 \
    --checkpoint results/training/checkpoints/train-xxx.pth \
    --mmaction2-config configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py \
    [--labels datasets/quadruped_action/classes.txt] \
    --output /tmp/pred.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import MMACTION2_DIR, QUADRUPED_CLASSES_FILE, TRAINING_WORK_DIR, CHECKPOINTS_DIR

# vendor 未 pip install -e 时，确保 mmaction 包可直接 import
sys.path.insert(0, MMACTION2_DIR)

TEST_PY = os.path.join(MMACTION2_DIR, "tools", "test.py")


def _cpu_patch_dir() -> str:
    """macOS MPS 不支持 float64，通过 sitecustomize 强制 CPU。"""
    d = os.path.join(TRAINING_WORK_DIR, ".cpu_sitecustomize")
    os.makedirs(d, exist_ok=True)
    sf = os.path.join(d, "sitecustomize.py")
    if not os.path.isfile(sf):
        with open(sf, "w", encoding="utf-8") as f:
            f.write(
                "import torch\n"
                "if hasattr(torch.backends, 'mps'):\n"
                "    torch.backends.mps.is_available = lambda: False\n"
            )
    return d


def load_labels(labels_path: str | None) -> list[str]:
    path = labels_path or QUADRUPED_CLASSES_FILE
    if not path or not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def infer_with_api(args) -> dict:
    if str(args.device).startswith("cpu"):
        import torch
        torch.backends.mps.is_available = lambda: False

    from mmaction.apis import inference_recognizer, init_recognizer  # type: ignore
    from mmengine.config import Config  # type: ignore

    cfg_path = args.mmaction2_config
    if not os.path.isabs(cfg_path):
        cfg_path = os.path.join(MMACTION2_DIR, cfg_path)
    cfg = Config.fromfile(cfg_path)
    if args.num_classes is not None:
        cfg.model.cls_head.num_classes = args.num_classes
    model = init_recognizer(cfg, args.checkpoint, device=args.device)
    result = inference_recognizer(model, args.video)
    labels = load_labels(args.labels)
    preds = []

    # mmaction2 1.2+ 返回 ActionDataSample 或 [ActionDataSample]，旧版返回 [(idx, score)]
    if isinstance(result, (list, tuple)) and result:
        samples = result if hasattr(result[0], "pred_score") else None
    elif hasattr(result, "pred_score"):
        samples = [result]
    else:
        samples = None

    if samples is not None:
        for sample in samples:
            scores = sample.pred_score
            if hasattr(scores, "cpu"):
                scores = scores.detach().cpu().numpy()
            sorted_idx = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
            for idx in sorted_idx:
                preds.append({
                    "label_index": int(idx),
                    "label": labels[int(idx)] if 0 <= int(idx) < len(labels) else str(idx),
                    "score": float(scores[idx]),
                })
    else:
        # 旧版 [(label_index, score), ...]
        for idx, score in result:
            preds.append({
                "label_index": int(idx),
                "label": labels[int(idx)] if 0 <= int(idx) < len(labels) else str(idx),
                "score": float(score),
            })
    return {
        "video": args.video,
        "checkpoint": args.checkpoint,
        "predictions": preds,
    }


def infer_with_test_py(args) -> dict:
    """无 API 环境时，生成单条 ann_file 走 tools/test.py，再解析 stdout。"""
    cfg_path = args.mmaction2_config
    if not os.path.isabs(cfg_path):
        cfg_path = os.path.join(MMACTION2_DIR, cfg_path)

    video_path = os.path.abspath(args.video)
    parent = os.path.dirname(video_path)
    with tempfile.TemporaryDirectory(prefix="mmaction_infer_") as tmpdir:
        ann = os.path.join(tmpdir, "infer_list.txt")
        with open(ann, "w", encoding="utf-8") as f:
            f.write(f"{os.path.basename(video_path)} 0\n")
        cmd = [
            sys.executable,
            TEST_PY,
            cfg_path,
            args.checkpoint,
            "--work-dir",
            tmpdir,
            "--launcher",
            "none",
            "--cfg-options",
            f"test_dataloader.dataset.ann_file={ann}",
            f"test_dataloader.dataset.data_prefix.video={parent}",
        ]
        if args.num_classes is not None:
            cmd.append(f"model.cls_head.num_classes={args.num_classes}")
        env = os.environ.copy()
        env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
        ppath = [str(MMACTION2_DIR), str(REPO)]
        if str(args.device).startswith("cpu"):
            ppath.insert(0, _cpu_patch_dir())
        if env.get("PYTHONPATH"):
            ppath.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(ppath)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(REPO),
        )
    labels = load_labels(args.labels)
    return {
        "video": args.video,
        "checkpoint": args.checkpoint,
        "predictions": [],
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-30:]),
        "returncode": proc.returncode,
        "note": "mmaction2 API 不可用，已回退到 tools/test.py；请安装依赖后使用 --use-api 或调用 server 推理端点。",
    }


def main() -> int:
    # PyTorch >=2.6 默认 weights_only=True，mmengine checkpoint 含 HistoryBuffer 会失败
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

    parser = argparse.ArgumentParser(description="mmaction2 single-video inference")
    parser.add_argument("--video", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--mmaction2-config", required=True)
    parser.add_argument("--labels", default=None)
    parser.add_argument("--num-classes", type=int, default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--use-api", action="store_true", help="强制使用 Python API")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if not os.path.isabs(args.checkpoint):
        args.checkpoint = os.path.join(CHECKPOINTS_DIR, os.path.basename(args.checkpoint))

    use_api = args.use_api
    if not use_api:
        try:
            import mmaction  # noqa: F401
            use_api = True
        except ImportError:
            use_api = False

    try:
        if use_api:
            result = infer_with_api(args)
        else:
            result = infer_with_test_py(args)
        result["inferred_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    out = json.dumps(result, ensure_ascii=False, indent=2)
    print(out)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    return 0 if result.get("returncode", 0) == 0 and "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
