#!/usr/bin/env python3
"""Create H.264 review clips from the frozen image pilot source manifest."""
import argparse
import csv
import json
import math
import os
import subprocess
from pathlib import Path


def source_samples(row, start):
    """Record decoded source positions; fail if frame/time metadata is inconsistent."""
    import cv2
    fps = float(row['fps'])
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('invalid source fps')
    capture = cv2.VideoCapture(row['source_path'], cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError(f"cannot open source {row['video']}")
    timestamps, frames = [], []
    try:
        for offset in (0.25, 0.75, 1.25, 1.75):
            target = start + offset
            frame = round(target * fps)
            if not capture.set(cv2.CAP_PROP_POS_FRAMES, frame):
                raise ValueError(f"source seek failed: {row['video']} frame {frame}")
            ok, image = capture.read()
            if not ok or image is None:
                raise ValueError(f"cannot decode source {row['video']} frame {frame}")
            actual_frame = round(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if actual_frame != frame:
                raise ValueError(f"source frame mismatch {row['video']}: {actual_frame} vs {frame}")
            actual = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(actual) or abs(actual - target) > 0.5:
                raise ValueError(f"source timestamp mismatch {row['video']}: {actual} vs {target}")
            timestamps.append({'target_sec': target, 'decoded_sec': actual,
                               'delta_sec': actual - target})
            frames.append(actual_frame)
    finally:
        capture.release()
    return timestamps, frames


def clip_starts(duration):
    if duration < 2:
        return []
    if duration < 4:
        return [(duration - 2) / 2]
    starts = [(duration - 2) / 4, 3 * (duration - 2) / 4]
    if starts[1] - starts[0] < 2:
        return starts[:1]
    return starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--limit', type=int, help='maximum source videos; for a small smoke run')
    parser.add_argument('--ffmpeg', default='ffmpeg', help='path to existing ffmpeg executable')
    parser.add_argument('--resume', action='store_true',
                        help='continue from progress.jsonl after an interrupted run')
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()) and not args.resume:
        raise ValueError('output directory must be empty')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'proxies').mkdir(exist_ok=True)
    with args.manifest.open(encoding='utf-8', newline='') as stream:
        sources = list(csv.DictReader(stream))
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError('limit must be positive')
        sources = sources[:args.limit]
    progress_path = args.out / 'progress.jsonl'
    items = []
    completed = set()
    if progress_path.exists():
        if not args.resume:
            raise ValueError('progress exists; use --resume to continue it')
        with progress_path.open(encoding='utf-8') as stream:
            for line in stream:
                item = json.loads(line)
                if not (args.out / item['path']).is_file():
                    raise ValueError(f"progress references missing clip: {item['path']}")
                items.append(item)
                completed.add(item['path'])
        print(f'resumed {len(items)} indexed clips', flush=True)
    for row in sources:
        duration = float(row['duration'])
        for index, start in enumerate(clip_starts(duration)):
            relative = f"proxies/{row['source_id']}_{index}.mp4"
            if relative in completed:
                continue
            timestamps, frames = source_samples(row, start)
            temporary = args.out / (relative + '.part.mp4')
            target_path = args.out / relative
            if target_path.exists() or temporary.exists():
                if not target_path.exists():
                    raise ValueError(f'unindexed partial proxy already exists: {relative}')
                # A proxy without a progress record failed validation or predates a crash.
                # Quarantine it rather than silently treating an unindexed file as valid.
                os.replace(target_path, args.out / (relative + '.invalid.mp4'))
            subprocess.run([args.ffmpeg, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(start),
                            '-i', row['source_path'], '-t', '2', '-an', '-vf',
                            f"setpts=PTS-STARTPTS,fps={float(row['fps'])},scale=1280:720:force_original_aspect_ratio=decrease", '-c:v', 'libx264',
                            '-threads', '1', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                            str(temporary)], check=True)
            os.replace(temporary, target_path)
            import cv2
            capture = cv2.VideoCapture(str(args.out / relative), cv2.CAP_FFMPEG,
                                       [cv2.CAP_PROP_N_THREADS, 1])
            try:
                if not capture.isOpened():
                    raise ValueError(f'cannot open proxy {relative}')
                fps = capture.get(cv2.CAP_PROP_FPS)
                count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                if fps <= 0 or count < 1:
                    raise ValueError(f'invalid proxy metadata {relative}')
                actual_duration = count / fps
                # One frame accommodates the encoder's subframe 2-second rounding.
                if abs(actual_duration - 2) > 1 / fps:
                    raise ValueError(f'incomplete proxy {relative}: {actual_duration}s')
            finally:
                capture.release()
            items.append({'path': relative, 'file': relative, 'source_id': row['source_id'],
                          'video': row['video'], 'start_sec': start, 'end_sec': start + 2,
                          'split': row['split'], 'domain': row['domain'], 'scenario': 'pilot',
                          'label_scope': 'any_pet_in_window', 'proxy_duration': actual_duration,
                          'sample_timestamps': timestamps, 'frame_ids': frames,
                          'review_status': 'unlabeled'})
            with progress_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(items[-1], ensure_ascii=False) + '\n')
        print(f"prepared {len(items)} clips; last source {row['source_id']}", flush=True)
    if not items:
        raise ValueError('no eligible clips')
    with (args.out / 'clips.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows({**item, 'sample_timestamps': json.dumps(item['sample_timestamps']),
                          'frame_ids': json.dumps(item['frame_ids'])} for item in items)
    (args.out / 'items.json').write_text(json.dumps({'count': len(items), 'items': items,
        'mode': 'video', 'hide_teacher': True, 'title': '视频标注 · 首轮',
        'description': '完整片段内出现过宠物即为有宠物'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'prepared {len(items)} clips from {len(sources)} sources')


if __name__ == '__main__':
    main()
