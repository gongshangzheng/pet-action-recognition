"""H.264 视频直写器：帧通过管道喂给 ffmpeg libx264，一步到位输出 QuickTime 可播的 MP4。

ffmpeg 二进制解析顺序：系统 ffmpeg → imageio_ffmpeg 自带静态二进制。
两者都不可用时回退 OpenCV mp4v（QuickTime 不认，需自行转码）。

用法：
    from petlib.videowriter import H264VideoWriter
    vw = H264VideoWriter("out.mp4", fps=15, size=(640, 640))
    vw.write(frame_bgr)  # 逐帧
    vw.release()
"""
from __future__ import annotations

import shutil
import subprocess

import cv2
import numpy as np


def _find_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


class H264VideoWriter:
    """libx264 直写器（yuv420p，QuickTime/浏览器通用）。"""

    def __init__(self, path: str, fps: float, size: tuple[int, int],
                 crf: int = 23, preset: str = "fast"):
        self.path = path
        self.fps = float(fps)
        self.size = (int(size[0]), int(size[1]))
        self._proc = None
        ffmpeg = _find_ffmpeg()
        if ffmpeg is None:
            self._fallback = cv2.VideoWriter(
                path, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, self.size)
            self._mode = "mp4v-fallback"
            if not self._fallback.isOpened():
                raise RuntimeError("H264VideoWriter: 无 ffmpeg 且 cv2 mp4v 打开失败")
            return
        cmd = [ffmpeg, "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "bgr24",
               "-s", f"{self.size[0]}x{self.size[1]}", "-r", str(self.fps),
               "-i", "-",
               "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
               "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               path]
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
        self._mode = "h264"

    @property
    def mode(self) -> str:
        return self._mode

    def write(self, frame_bgr: np.ndarray) -> None:
        if frame_bgr.shape[1] != self.size[0] or frame_bgr.shape[0] != self.size[1]:
            frame_bgr = cv2.resize(frame_bgr, self.size)
        if self._mode == "h264":
            self._proc.stdin.write(frame_bgr.tobytes())
        else:
            self._fallback.write(frame_bgr)

    def release(self) -> None:
        if self._proc is not None:
            self._proc.stdin.close()
            self._proc.wait()
            self._proc = None
        elif self._fallback is not None:
            self._fallback.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
