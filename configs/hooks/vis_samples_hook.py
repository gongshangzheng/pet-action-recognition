"""训练中定期可视化 Hook — 每 N epoch 对固定 val 样本生成预测可视化图。

通过 --cfg-options custom_hooks=[dict(type='VisSamplesHook', interval=10, ...)] 注入。
在 runner 训练进程内运行，直接拿 runner.model 推理，不需额外加载 checkpoint。

产物：work_dir/vis_samples/epoch_N/sample_K.jpg + meta.json
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np
from mmengine.hooks import Hook
from mmengine.registry import HOOKS


def _read_samples(ann_file: str, num_samples: int):
    """从 ann_file 均匀采样固定 N 个 (rel_path, label)。"""
    samples = []
    with open(ann_file, "r") as f:
        for ln in f:
            parts = ln.strip().split()
            if len(parts) >= 2:
                samples.append((parts[0], int(parts[1])))
    if not samples:
        return []
    step = max(1, len(samples) // num_samples)
    return samples[::step][:num_samples]


def _read_labels(dataset_root: str):
    """从 dataset_root 下找 label_map 文件。"""
    for lm in [
        os.path.join(dataset_root, "annotation", "labels.txt"),
        os.path.join(dataset_root, "classes.txt"),
    ]:
        if os.path.isfile(lm):
            with open(lm) as f:
                return [ln.strip() for ln in f if ln.strip()]
    return []


@HOOKS.register_module()
class VisSamplesHook(Hook):
    """每 N epoch 结束后，对固定 val 样本生成可视化图（margin 边条 GT+pred+top5）。

    Args:
        interval (int): 每 N epoch 生成一次（默认 10）。
        num_samples (int): 每次采样多少个 val 样本（默认 6）。
        ann_file (str): val ann_file 路径（相对 cwd 或绝对）。
        data_root (str): data_prefix.video 路径（val 视频根目录）。
        dataset_root (str): 数据集根目录（用于找 label_map）。
    """

    priority = "LOW"

    def __init__(
        self,
        interval: int = 10,
        num_samples: int = 6,
        ann_file: str = "",
        data_root: str = "",
        dataset_root: str = "",
    ):
        self.interval = interval
        self.num_samples = num_samples
        self.ann_file = ann_file
        self.data_root = data_root
        self.dataset_root = dataset_root
        self.samples: list[tuple[str, int]] = []
        self.labels: list[str] = []
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self._initialized = False

    def _lazy_init(self):
        """延迟初始化（在 runner 启动后，work_dir 已确定时）。"""
        if self._initialized:
            return
        self._initialized = True
        if not self.ann_file or not os.path.isfile(self.ann_file):
            # 尝试相对路径
            cwd = os.getcwd()
            full = os.path.join(cwd, self.ann_file) if not os.path.isabs(self.ann_file) else self.ann_file
            if os.path.isfile(full):
                self.ann_file = full
        if self.ann_file:
            self.samples = _read_samples(self.ann_file, self.num_samples)
        if self.dataset_root:
            self.labels = _read_labels(self.dataset_root)
        elif self.data_root:
            self.labels = _read_labels(os.path.dirname(self.data_root))
        if self.samples:
            print(f"[VisSamplesHook] loaded {len(self.samples)} samples, {len(self.labels)} labels, interval={self.interval}")

    def after_epoch(self, runner) -> None:
        epoch = runner.epoch + 1  # mmengine epoch 从 0 开始
        if epoch % self.interval != 0:
            return
        self._lazy_init()
        if not self.samples:
            return

        work_dir = runner.work_dir
        vis_dir = os.path.join(work_dir, "vis_samples", f"epoch_{epoch}")
        os.makedirs(vis_dir, exist_ok=True)

        model = runner.model
        if hasattr(model, "module"):
            model = model.module  # DDP wrapper
        model.eval()
        import torch

        results_meta = []
        for idx, (rel_path, gt_label) in enumerate(self.samples):
            video_path = self._resolve_video(rel_path)
            if not video_path or not os.path.isfile(video_path):
                continue
            try:
                meta = self._gen_one(model, video_path, gt_label, idx, vis_dir, epoch, torch)
                if meta:
                    results_meta.append(meta)
            except Exception as e:
                print(f"[VisSamplesHook] sample {idx} failed: {e}")

        if results_meta:
            meta_path = os.path.join(vis_dir, "meta.json")
            with open(meta_path, "w") as f:
                json.dump({"epoch": epoch, "samples": results_meta}, f, ensure_ascii=False, indent=2)
            print(f"[VisSamplesHook] epoch {epoch}: {len(results_meta)} samples -> vis_samples/epoch_{epoch}/")

    def _resolve_video(self, rel_path: str) -> str:
        if os.path.isabs(rel_path):
            return rel_path
        for base in [self.data_root, self.dataset_root]:
            if base:
                full = os.path.join(base, rel_path)
                if os.path.isfile(full):
                    return full
                # data_root 可能是数据集根（ann_file 路径已含 dataset/video/）
                full = os.path.join(os.path.dirname(base), rel_path)
                if os.path.isfile(full):
                    return full
        return os.path.join(os.getcwd(), rel_path)

    def _gen_one(self, model, video_path, gt_label, idx, vis_dir, epoch, torch):
        from mmaction.apis import inference_recognizer

        result = inference_recognizer(model, video_path)
        scores = result.pred_score
        if hasattr(scores, "detach"):
            scores = scores.detach().cpu().numpy()
        scores = np.asarray(scores)

        top1_idx = int(scores.argmax())
        top1_score = float(scores[top1_idx])
        top1_label = self.labels[top1_idx] if top1_idx < len(self.labels) else str(top1_idx)
        gt_name = self.labels[gt_label] if gt_label < len(self.labels) else str(gt_label)

        # top5
        order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
        top5 = [
            (self.labels[i] if i < len(self.labels) else str(i), float(scores[i]))
            for i in order[:5]
        ]

        # 取中间帧
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 2:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return None

        # margin 布局
        h, w = frame.shape[:2]
        scale = max(0.4, min(w, h) / 700.0)
        thick = max(1, int(round(scale * 2)))
        line_h = max(18, int(24 * scale))
        top_h = max(30, line_h + 14)
        bottom_h = max(40, len(top5[:5]) * line_h + 12)
        canvas_h = h + top_h + bottom_h
        canvas = np.zeros((canvas_h, w, 3), dtype=np.uint8)
        canvas[top_h : top_h + h] = frame

        gt_text = f"GT: {gt_name}"
        pred_text = f"pred: {top1_label} ({top1_score:.2f})"
        pred_color = (0, 255, 0) if top1_idx == gt_label else (0, 0, 255)

        ty = top_h // 2 + line_h // 3
        cv2.putText(canvas, gt_text, (10, ty), self.font, scale, (0, 255, 0), thick, cv2.LINE_AA)
        (gw, _), _ = cv2.getTextSize(gt_text, self.font, scale, thick)
        cv2.putText(canvas, pred_text, (10 + gw + 20, ty), self.font, scale, pred_color, thick, cv2.LINE_AA)

        by = top_h + h + line_h
        for i, (lbl, sc) in enumerate(top5[:5]):
            cv2.putText(
                canvas, f"{i+1}. {lbl} {sc:.2f}", (10, by + i * line_h),
                self.font, scale * 0.8, (255, 255, 255), max(1, thick - 1), cv2.LINE_AA,
            )

        jpg_path = os.path.join(vis_dir, f"sample_{idx}.jpg")
        cv2.imwrite(jpg_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return {
            "idx": idx,
            "file": f"sample_{idx}.jpg",
            "gt_label": gt_name,
            "pred_label": top1_label,
            "score": round(top1_score, 3),
            "correct": top1_idx == gt_label,
        }
