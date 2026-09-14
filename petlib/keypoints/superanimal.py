"""SuperAnimal-Quadruped 关键点提取器（DeepLabCut 生态）。

依赖：deeplabcut（独立安装；未安装时给出安装指引）。
骨架：四足 26 点定义（DLC 模型 zoo），与 canon-17 映射见 scripts/keypoint_mapping_quadruped.json。
"""
from __future__ import annotations

from petlib.keypoints.base import KeypointExtractor


class SuperAnimalExtractor(KeypointExtractor):
    name = "superanimal"
    num_keypoints = 26

    def __init__(self, **kwargs):
        try:
            import deeplabcut  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "SuperAnimal 需要 deeplabcut：参考 remote-servers/datasets skill 的安装指引"
            ) from exc

    def extract(self, video_path: str, boxes: list[tuple] | None = None) -> KeypointSequence:
        import deeplabcut

        # Modelzoo 零样本推理（视频级）；框先验暂不使用（DLC 全帧推理）
        deeplabcut.video_inference_superanimal(
            videos=[video_path],
            superanimal_name="superanimal_quadruped",
            videotype="mp4",
            destproject="/tmp/sa_project",
            video_adapt=False,
        )
        # TODO(§5)：解析 DLC h5 → KeypointSequence（含 canon-17 映射）
        raise NotImplementedError("DLC h5 → NPZ 解析在 §5 任务中补齐")
