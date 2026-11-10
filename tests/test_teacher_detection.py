import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
from lib.detection.teacher import detect_video


def test_real_video_selected_frames_reach_detector():
    root = Path(__file__).resolve().parents[1] / 'results/tests/teacher-detection'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as directory:
        video = Path(directory) / 'source.avi'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter.fourcc(*'MJPG'), 10, (32, 32))
        assert writer.isOpened()
        for index in range(12):
            writer.write(np.full((32, 32, 3), index * 15, dtype=np.uint8))
        writer.release()

        class RecordingDetector:
            def __init__(self):
                self.values = []

            def detect(self, frame, classes):
                assert classes == ('cat', 'dog')
                self.values.append(round(float(frame.mean())))
                return []

        detector = RecordingDetector()
        records = list(detect_video(video, detector))
        assert [row['frame'] for row in records] == [0, 5, 10]
        assert [row['candidates'] for row in records] == [[], [], []]
        assert detector.values == [0, 75, 150]
        assert all(json.loads(json.dumps(row)) == row for row in records)
