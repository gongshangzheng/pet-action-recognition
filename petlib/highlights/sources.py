"""宠物身体来源与猫脸来源的统一接口。

重依赖（ultralytics）在实现类构造时才 import；OpenCV 是基础依赖。
所有坐标都是“分析分辨率”像素。
"""
from __future__ import annotations

import json
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from petlib.highlights.metrics import Box, clip_box, expand_box

COCO_PET_CLASSES = {15: "cat", 16: "dog"}


@dataclass
class PetObservation:
    box: Box
    conf: float = 1.0
    cls: str = "cat"
    mask: np.ndarray | None = None  # (H, W) bool，分析分辨率；None 表示只有框


@dataclass
class FaceObservation:
    box: Box
    conf: float = 1.0


class PetSource(ABC):
    name = "base"
    area_source = "box"  # "mask" | "box" | "none"

    def configure(self, source_size: tuple[int, int], analysis_size: tuple[int, int]) -> None:
        """处理前调用：source_size / analysis_size 均为 (W, H)。"""
        self.source_size = source_size
        self.analysis_size = analysis_size

    @abstractmethod
    def observe(self, frame_bgr: np.ndarray, frame_index: int) -> list[PetObservation]:
        """返回该帧所有宠物（可为空）。frame_index 为原视频帧号（0 起）。"""


class NoPetSource(PetSource):
    name = "none"
    area_source = "none"

    def observe(self, frame_bgr, frame_index):
        return []


class TrackJsonPetSource(PetSource):
    """读取 `scripts/pet_detect_track.py` 的 track.json（`smooth_track[].box`，原分辨率）。"""

    name = "track_json"
    area_source = "box"

    def __init__(self, path: str | os.PathLike, max_gap: int = 0):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        records = data.get("smooth_track", data if isinstance(data, list) else [])
        self.boxes: dict[int, tuple[Box, float]] = {}
        for rec in records:
            if rec.get("box") is None:
                continue
            self.boxes[int(rec["frame"])] = (tuple(float(v) for v in rec["box"]), float(rec.get("conf", 1.0)))
        self.max_gap = max_gap
        self.source_frames = data.get("frames") if isinstance(data, dict) else None

    def observe(self, frame_bgr, frame_index):
        hit = self.boxes.get(frame_index)
        if hit is None and self.max_gap:
            for d in range(1, self.max_gap + 1):
                hit = self.boxes.get(frame_index - d) or self.boxes.get(frame_index + d)
                if hit:
                    break
        if hit is None:
            return []
        (x1, y1, x2, y2), conf = hit
        sx = self.analysis_size[0] / self.source_size[0]
        sy = self.analysis_size[1] / self.source_size[1]
        return [PetObservation(box=(x1 * sx, y1 * sy, x2 * sx, y2 * sy), conf=conf)]


class YoloSegPetSource(PetSource):
    """ultralytics YOLO 实例分割（默认 YOLO11n-seg），只保留 COCO cat/dog。"""

    name = "yolo_seg"
    area_source = "mask"

    def __init__(self, weights: str = "yolo11n-seg.pt", conf: float = 0.25,
                 imgsz: int = 640, device: str | None = None,
                 classes: tuple[int, ...] = (15, 16)):
        if not Path(weights).is_file():
            raise FileNotFoundError(f"YOLO weights not found (no auto-download): {weights}")
        from ultralytics import YOLO  # 懒加载

        self.model = YOLO(weights)
        self.weights = str(weights)
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self.classes = list(classes)

    def observe(self, frame_bgr, frame_index):
        import cv2

        # agnostic_nms：同一只猫常被同时判成 cat 和 dog，跨类别去重
        res = self.model.predict(frame_bgr, conf=self.conf, imgsz=self.imgsz, device=self.device,
                                 classes=self.classes, agnostic_nms=True, verbose=False)[0]
        if res.boxes is None or len(res.boxes) == 0:
            return []
        h, w = frame_bgr.shape[:2]
        xyxy = res.boxes.xyxy.cpu().numpy()
        confs = res.boxes.conf.cpu().numpy()
        clss = res.boxes.cls.cpu().numpy().astype(int)
        polys = res.masks.xy if res.masks is not None else [None] * len(xyxy)
        out = []
        for box, c, k, poly in zip(xyxy, confs, clss, polys):
            mask = None
            if poly is not None and len(poly) >= 3:
                mask_u8 = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask_u8, [np.round(poly).astype(np.int32)], 1)
                mask = mask_u8.astype(bool)
            out.append(PetObservation(box=tuple(float(v) for v in box), conf=float(c),
                                      cls=COCO_PET_CLASSES.get(int(k), str(k)), mask=mask))
        return out


class FaceSource(ABC):
    name = "base"

    @abstractmethod
    def detect(self, frame_bgr: np.ndarray, pet_boxes: list[Box] | None) -> list[FaceObservation]:
        """pet_boxes 为 None 表示没有宠物来源（整帧检测）；空列表表示本帧无宠物。"""


class NoFaceSource(FaceSource):
    name = "none"

    def detect(self, frame_bgr, pet_boxes):
        return []


def find_cat_face_cascade(filename: str = "haarcascade_frontalcatface_extended.xml") -> str | None:
    """按 cv2.data → conda/系统常见目录查找 OpenCV 自带猫脸级联文件。"""
    import cv2

    candidates = []
    data = getattr(cv2, "data", None)
    if data is not None and getattr(data, "haarcascades", None):
        candidates.append(Path(data.haarcascades))
    prefix = Path(sys.prefix)
    candidates += [
        Path(cv2.__file__).resolve().parent / "data",
        prefix / "Library" / "etc" / "haarcascades",
        prefix / "share" / "opencv4" / "haarcascades",
        prefix / "share" / "OpenCV" / "haarcascades",
        Path("/usr/share/opencv4/haarcascades"),
        Path("/usr/share/opencv/haarcascades"),
        Path("/usr/local/share/opencv4/haarcascades"),
    ]
    for d in candidates:
        p = d / filename
        if p.is_file():
            return str(p)
    return None


def _iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class HaarCatFaceSource(FaceSource):
    """OpenCV 自带正面猫脸 Haar 级联；有宠物框时只在框内检测。"""

    name = "haar_frontalcatface_extended"

    def __init__(self, cascade_path: str | None = None, roi_expand: float = 0.1,
                 min_roi: int = 160, scale_factor: float = 1.1, min_neighbors: int = 3,
                 min_size: int = 24):
        import cv2

        path = cascade_path or find_cat_face_cascade()
        if not path or not Path(path).is_file():
            raise FileNotFoundError("haarcascade_frontalcatface_extended.xml not found; pass --face-cascade")
        self.cascade = cv2.CascadeClassifier(path)
        if self.cascade.empty():
            raise RuntimeError(f"failed to load cascade: {path}")
        self.cascade_path = path
        self.roi_expand = roi_expand
        self.min_roi = min_roi
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size

    def _detect_gray(self, gray: np.ndarray) -> list[Box]:
        rects = self.cascade.detectMultiScale(gray, scaleFactor=self.scale_factor,
                                              minNeighbors=self.min_neighbors,
                                              minSize=(self.min_size, self.min_size))
        return [(float(x), float(y), float(x + w), float(y + h)) for (x, y, w, h) in rects]

    def detect(self, frame_bgr, pet_boxes):
        import cv2

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
        gray = cv2.equalizeHist(gray)
        h, w = gray.shape
        if pet_boxes is None:
            return [FaceObservation(b) for b in self._detect_gray(gray)]
        faces: list[Box] = []
        for pb in pet_boxes:
            x1, y1, x2, y2 = clip_box(expand_box(pb, self.roi_expand), w, h)
            if x2 - x1 < 8 or y2 - y1 < 8:
                continue
            roi = gray[y1:y2, x1:x2]
            scale = max(1.0, self.min_roi / min(roi.shape))
            if scale > 1.0:
                roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            for fx1, fy1, fx2, fy2 in self._detect_gray(roi):
                faces.append((x1 + fx1 / scale, y1 + fy1 / scale, x1 + fx2 / scale, y1 + fy2 / scale))
        kept: list[Box] = []
        for f in sorted(faces, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True):
            if all(_iou(f, k) < 0.5 for k in kept):
                kept.append(f)
        return [FaceObservation(b) for b in kept]


def build_pet_source(kind: str, **kw) -> PetSource:
    if kind == "none":
        return NoPetSource()
    if kind == "track_json":
        return TrackJsonPetSource(kw["track_json"])
    if kind == "yolo_seg":
        return YoloSegPetSource(weights=kw.get("weights") or "yolo11n-seg.pt",
                                conf=kw.get("conf", 0.25), device=kw.get("device"))
    raise ValueError(f"unknown pet source: {kind}")


def build_face_source(kind: str, **kw) -> FaceSource:
    if kind == "none":
        return NoFaceSource()
    if kind == "haar":
        return HaarCatFaceSource(cascade_path=kw.get("cascade_path"))
    raise ValueError(f"unknown face source: {kind}")
