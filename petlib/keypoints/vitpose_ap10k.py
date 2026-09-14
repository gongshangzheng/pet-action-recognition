"""ViTPose-AP10K 关键点提取器（MMPose 动物动物园）。

依赖：mmpose 1.x + mmdet（独立环境安装；AP-10K 权重经 openmmlab 下载）。
骨架：AP-10K 17 点（与 scripts/keypoint_mapping_quadruped.json 的 canon-17 对齐）。
"""
from __future__ import annotations

from petlib.keypoints.base import KeypointExtractor


class VitPoseAp10kExtractor(KeypointExtractor):
    name = "vitpose_ap10k"
    num_keypoints = 17

    def __init__(self, config: str | None = None, checkpoint: str | None = None, device: str = "cuda:0", **kwargs):
        try:
            from mmpose.apis import init_model  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "ViTPose 需要 mmpose：pip install mmpose（plf 环境；权重 openmmlab 下载）"
            ) from exc
        import mmengine.config

        self.config = config or "configs/animal_2d_keypoint/topdown_heatmap/ap10k/td-hm_ViTPose-base_8xb64-210e_ap10k-256x200.py"
        self.checkpoint = checkpoint or "https://download.openmmlab.com/mmpose/animal/2d_animalpose/td-hm_ViTPose-base_8xb64-210e_ap10k-256x200/td-hm_ViTPose-base_8xb64-210e_ap10k-256x200-29885ce8_20211022.pth"
        self.device = device
        self._model = None  # 首次 extract 时初始化（避免 import 即占 GPU）

    def extract(self, video_path: str, boxes: list[tuple] | None = None) -> KeypointSequence:
        import numpy as np

        from mmpose.apis import inference_topdown, init_model

        if self._model is None:
            self._model = init_model(self.config, self.checkpoint, device=self.device)
        cap = __import__("cv2").VideoCapture(video_path)
        results = []
        frame_inds = []
        fi = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            bboxes = np.array([boxes[fi]], dtype=np.float32) if boxes and fi < len(boxes) else None
            r = inference_topdown(self._model, frame, bboxes=bboxes)
            preds = r[0].pred_instances
            kp = preds.keypoints[0]  # (V, 2)
            sc = preds.keypoint_scores[0]  # (V,)
            results.append(np.concatenate([kp, sc[:, None]], axis=1))
            frame_inds.append(fi)
            fi += 1
        cap.release()
        kp = np.stack(results).astype(np.float32)  # (T, V, 3)
        return KeypointSequence(
            kp=kp.astype(np.float16), frame_inds=frame_inds,
            total_frames=fi, source=video_path)
