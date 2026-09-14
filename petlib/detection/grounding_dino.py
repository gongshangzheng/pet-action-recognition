"""GroundingDINO 检测器（transformers 原生实现，开放词汇）。

权重：本地目录（默认 ~/models/grounding-dino-tiny，经 hf-mirror 下载）。
重依赖（transformers/torch/PIL）全部懒加载。
"""
from __future__ import annotations

import os
from pathlib import Path

from petlib.detection.base import Detector
from petlib.schemas import Detection


class GroundingDinoDetector(Detector):
    name = "grounding_dino"

    def __init__(self, model_dir: str | None = None, box_threshold: float = 0.3,
                 text_threshold: float = 0.25, device: str = "cuda:0"):
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        import torch  # 懒加载
        from transformers import AutoProcessor, GroundingDinoForObjectDetection

        self.device = device if torch.cuda.is_available() else "cpu"
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self.model_dir = str(Path(model_dir or Path.home() / "models/grounding-dino-tiny").expanduser())
        self._processor = AutoProcessor.from_pretrained(self.model_dir)
        self._model = GroundingDinoForObjectDetection.from_pretrained(self.model_dir).to(self.device)
        self._model.eval()

    def detect(self, img_bgr, classes: tuple[str, ...] = ("cat",)):
        import cv2
        from PIL import Image

        text_prompt = " ".join(f"{c}." for c in classes)
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        inputs = self._processor(images=pil, text=text_prompt, return_tensors="pt").to(self.device)
        with __import__("torch").no_grad():
            out = self._model(**inputs)
        H, W = img_bgr.shape[:2]
        res = self._processor.post_process_grounded_object_detection(
            out, input_ids=inputs.input_ids, threshold=self.box_threshold,
            text_threshold=self.text_threshold, target_sizes=[(H, W)])[0]
        dets: list[Detection] = []
        for box, score, label in zip(res["boxes"].cpu().numpy(),
                                     res["scores"].cpu().numpy(),
                                     res["labels"]):
            phrase = str(label)
            cls = next((c for c in classes if c in phrase), classes[0] if classes else "object")
            dets.append(Detection(frame=-1, box=tuple(float(v) for v in box),
                                  conf=float(score), cls=cls))
        dets.sort(key=lambda d: -d.conf)
        return dets
