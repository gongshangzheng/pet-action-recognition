"""SORT 核心：共享的卡尔曼滤波 + 匈牙利匹配（供 SORT 系实现复用）。

简化实现（常速模型，8 维状态 [cx,cy,w,h,vcx,vcy,vw,vh]）。
IoU 关联用 scipy.optimize.linear_sum_assignment。
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (N,4) xyxy, b: (M,4) xyxy → (N,M) IoU。"""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    xx1 = np.maximum(a[:, None, 0], b[None, :, 0])
    yy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    xx2 = np.minimum(a[:, None, 2], b[None, :, 2])
    yy2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter
    return inter / np.clip(union, 1e-6, None)


def associate(tracks_boxes: np.ndarray, dets_boxes: np.ndarray,
              iou_threshold: float = 0.3) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """匈牙利匹配。返回 (matches[(t,d)], unmatched_tracks, unmatched_dets)。"""
    if len(tracks_boxes) == 0:
        return [], [], list(range(len(dets_boxes)))
    if len(dets_boxes) == 0:
        return [], list(range(len(tracks_boxes))), []
    iou = iou_matrix(tracks_boxes, dets_boxes)
    cost = 1.0 - iou
    rows, cols = linear_sum_assignment(cost)
    matches, unmatched_t, unmatched_d = [], [], []
    for r in range(len(tracks_boxes)):
        if r in rows and iou[r, cols[list(rows).index(r)]] >= iou_threshold:
            matches.append((r, int(cols[list(rows).index(r)])))
        else:
            unmatched_t.append(r)
    for c in range(len(dets_boxes)):
        if c not in cols:
            unmatched_d.append(c)
    return matches, unmatched_t, unmatched_d


class KalmanBoxTracker:
    """常速卡尔曼滤波的单目标跟踪器（8 维状态）。"""

    count = 0

    def __init__(self, box: np.ndarray, conf: float = 0.0):
        self.kf = np.zeros(8)
        cx, cy, x2, y2 = box
        w, h = x2 - cx, y2 - cy
        self.kf[:4] = [cx, cy, w, h]
        self.P = np.eye(8) * 10.0
        self.P[4:, 4:] *= 1000.0
        self.F = np.eye(8)
        for i in range(4):
            self.F[i, i + 4] = 1.0
        self.Q = np.eye(8) * 0.01
        self.H = np.zeros((4, 8))
        self.H[:4, :4] = np.eye(4)
        self.R = np.diag([1.0, 1.0, 10.0, 10.0])
        self.conf = conf
        self.hits = 1
        self.age = 0
        self.time_since_update = 0
        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count

    def predict(self) -> np.ndarray:
        self.kf = self.F @ self.kf
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.age += 1
        self.time_since_update += 1
        return self.kf[:4].copy()

    def update(self, box: np.ndarray, conf: float = 0.0) -> None:
        cx, cy, x2, y2 = box
        z = np.array([cx, cy, x2 - cx, y2 - cy])
        y = z - self.H @ self.kf
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.kf = self.kf + K @ y
        self.P = (np.eye(8) - K @ self.H) @ self.P
        self.conf = conf
        self.hits += 1
        self.time_since_update = 0

    @property
    def box(self) -> np.ndarray:
        cx, cy, w, h = self.kf[:4]
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])
