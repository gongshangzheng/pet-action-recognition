"""Run the teacher detector on selected frames of one video."""

import argparse
import contextlib
import json
import sys
from pathlib import Path

from lib.detection.anchors import select_frame_indices


def detect_video(video, detector):
    """Yield raw candidates for each decoded frame on the shared phase."""
    import cv2

    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f'Cannot open video: {video}')
    index = 0
    try:
        while capture.grab():
            if index in select_frame_indices(index + 1):
                ok, frame = capture.retrieve()
                if not ok:
                    raise RuntimeError(f'Cannot decode sampled frame {index}: {video}')
                with contextlib.redirect_stdout(sys.stderr):
                    detections = detector.detect(frame, classes=('cat', 'dog'))
                yield {'frame': index, 'candidates': [
                    {'class': item.cls, 'box': [float(v) for v in item.box],
                     'confidence': float(item.conf)} for item in detections]}
            index += 1
        if index == 0:
            raise RuntimeError(f'Video has no decoded frames: {video}')
    finally:
        capture.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--box-threshold', type=float, required=True)
    parser.add_argument('--text-threshold', type=float, required=True)
    args = parser.parse_args()
    if not (args.model_dir / 'config.json').is_file():
        raise FileNotFoundError(f'GroundingDINO model directory is incomplete: {args.model_dir}')
    from lib.detection.grounding_dino import GroundingDinoDetector

    with contextlib.redirect_stdout(sys.stderr):
        detector = GroundingDinoDetector(model_dir=str(args.model_dir), device=args.device,
                                         box_threshold=args.box_threshold,
                                         text_threshold=args.text_threshold)
    for record in detect_video(args.video, detector):
        print(json.dumps(record, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
