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


def _annotate_video_cv2(video: str, out_path: str, gt_label: str | None,
                         top1: tuple, top5: list[tuple]) -> None:
    """用 cv2 给视频加 margin 边条，标签写在边条里——视频画面不被字覆盖。

    上边条：GT（绿）+ pred top1（黄）；下边条：top5（白）。中间原帧不动。
    检测模型（未来）：若有 bbox，标签贴框边（cv2.rectangle + 框上方小字），不走全局边条。
    ActionVisualizer 检查 'pred_labels'（复数）但 inference_recognizer 返回 pred_label（单数）→
    画不了；且 GT 标签空间不匹配。故改 cv2 手动画在边条。
    """
    import cv2
    import numpy as np
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"cv2 打不开视频: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 字号适中，按短边自适应；边条高度容纳文字即可
    scale = max(0.4, min(w, h) / 700.0)
    thick = max(1, int(round(scale * 2)))
    line_h = max(18, int(24 * scale))
    top_h = max(30, line_h + 14)                       # 上边条：一行 GT + pred
    bottom_h = max(40, len(top5[:5]) * line_h + 12)    # 下边条：top5
    canvas_h = h + top_h + bottom_h
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, canvas_h))
    font = cv2.FONT_HERSHEY_SIMPLEX

    gt_text = f"GT: {gt_label}" if gt_label else "GT: (none)"
    pred_text = f"pred: {top1[0]} ({top1[1]:.2f})"

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        canvas = np.zeros((canvas_h, w, 3), dtype=np.uint8)  # 黑边条
        canvas[top_h:top_h + h] = frame                       # 帧居中
        # 上边条：GT + pred 同一行
        ty = top_h // 2 + line_h // 3
        cv2.putText(canvas, gt_text, (10, ty), font, scale, (0, 255, 0), thick, cv2.LINE_AA)   # 绿
        (gw, _), _ = cv2.getTextSize(gt_text, font, scale, thick)
        cv2.putText(canvas, pred_text, (10 + gw + 20, ty), font, scale, (0, 255, 255), thick, cv2.LINE_AA)  # 黄
        # 下边条：top5
        by = top_h + h + line_h
        for i, (lbl, sc) in enumerate(top5[:5]):
            cv2.putText(canvas, f"{i+1}. {lbl} {sc:.2f}", (10, by + i * line_h),
                        font, scale * 0.8, (255, 255, 255), max(1, thick - 1), cv2.LINE_AA)  # 白
        writer.write(canvas)
    cap.release()
    writer.release()


def infer_and_annotate(
    video: str,
    cfg,
    checkpoint: str,
    labels: list[str],
    out_video_path: Optional[str] = None,
    device: str = "cuda:0",
    gt_label: Optional[str] = None,
) -> dict:
    """对单视频推理；可选写标注 mp4（cv2 叠 GT + pred + top5）。

    Args:
        video: 视频文件路径。
        cfg: mmengine Config 对象（调用方已 fromfile + 必要 override）。
        checkpoint: checkpoint 文件路径。
        labels: 类名列表（K400 等），index=行号。
        out_video_path: 给定时写标注 mp4；None 则只返回预测。
        device: 'cuda:0' / 'cpu'。
        gt_label: 真实标签名（从视频路径派生，如 UCF101 的类名）；画在帧上对照。

    Returns:
        {top1_label, top1_score, top5, gpu_mem_mb}
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
        if video.startswith(("http://", "https://")):
            raise NotImplementedError("http(s) video 不支持出标注视频，请用本地路径")
        _annotate_video_cv2(video, out_video_path, gt_label, top1, top5)

    return {"top1_label": top1[0], "top1_score": top1[1], "top5": top5, "gpu_mem_mb": gpu_mem_mb}

