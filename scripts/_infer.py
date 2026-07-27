#!/usr/bin/env python3
"""共享：单视频推理 + （可选）标注视频生成。

inference.py（JSON-only）与 speedrun.py（出标注视频）都调它，避免重复。
"""
from __future__ import annotations

import os
from typing import Optional


def load_labels(labels_path: str) -> list[str]:
    """读 label_map（每行一个类名，index=行号；mmaction2 约定）。"""
    with open(labels_path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _extract_topk(result, labels: list[str], k: int = 5) -> list[tuple]:
    """从 inference_recognizer 的 result 提取 top-k [(label, score), ...]。

    mmaction2 1.2+ 返回 ActionDataSample（result.pred_score）；
    旧版返回 [(label_index, score), ...]。
    """
    import numpy as np

    if hasattr(result, "pred_score"):
        scores = result.pred_score
        if hasattr(scores, "detach"):
            scores = scores.detach().cpu().numpy()
        scores = np.asarray(scores)
        order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
        return [
            (labels[i] if i < len(labels) else str(i), float(scores[i]))
            for i in order[:k]
        ]
    # 旧版 [(idx, score), ...]
    out = []
    for idx, score in result:
        i = int(idx)
        out.append((labels[i] if i < len(labels) else str(i), float(score)))
    return out


def infer_and_annotate(
    video: str,
    cfg,
    checkpoint: str,
    labels: list[str],
    out_video_path: Optional[str] = None,
    device: str = "cuda:0",
    fps: int = 30,
) -> dict:
    """对单视频推理；可选写标注 mp4。

    Args:
        video: 视频文件路径（CIFS/本地均可，http 会 NotImplementedError）。
        cfg: mmengine Config 对象（调用方已 fromfile + 必要 override，如 num_classes）。
        checkpoint: checkpoint 文件路径。
        labels: 类名列表（K400 等），index=行号。
        out_video_path: 给定时用 ActionVisualizer 把 top-5 叠帧写 mp4；None 则只返回预测。
        device: 'cuda:0' / 'cpu'。

    Returns:
        {top1_label, top1_score, top5: [(label, score), ...]}
    """
    from mmaction.apis import inference_recognizer, init_recognizer

    # GPU 显存峰值统计（speed run 的基础资源指标；按指定 device 测量）
    gpu_mem_mb = None
    try:
        import torch
        dev = torch.device(device)
        if torch.cuda.is_available() and dev.type == "cuda":
            torch.cuda.reset_peak_memory_stats(dev)
    except Exception:
        pass

    model = init_recognizer(cfg, checkpoint, device=device)
    result = inference_recognizer(model, video)

    try:
        import torch
        dev = torch.device(device)
        if torch.cuda.is_available() and dev.type == "cuda":
            gpu_mem_mb = round(torch.cuda.max_memory_allocated(dev) / 1e6, 1)
    except Exception:
        pass

    top5 = _extract_topk(result, labels, k=5)
    top1 = top5[0] if top5 else ("", 0.0)

    if out_video_path:
        # ActionVisualizer 写标注视频（复刻 models/mmaction2/demo/demo.py:56-108）
        # 注意：不 subprocess demo.py——它把 out_path 强写成 <cwd>/demo/。
        if video.startswith(("http://", "https://")):
            raise NotImplementedError("http(s) video 不支持出标注视频，请用本地路径")
        from mmaction.visualization import ActionVisualizer

        os.makedirs(os.path.dirname(out_video_path), exist_ok=True)
        viz = ActionVisualizer()
        viz.dataset_meta = dict(classes=labels)
        viz.add_datasample(
            os.path.basename(out_video_path),
            video,
            result,
            draw_pred=True,
            draw_gt=False,
            text_cfg={"colors": "white"},
            fps=fps,
            out_type="video",
            out_path=out_video_path,
        )

    return {"top1_label": top1[0], "top1_score": top1[1], "top5": top5, "gpu_mem_mb": gpu_mem_mb}
