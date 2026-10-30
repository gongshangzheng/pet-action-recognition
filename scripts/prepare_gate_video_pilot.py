#!/usr/bin/env python3
"""Create H.264 review clips from the frozen image pilot source manifest."""
import argparse
import csv
import json
import subprocess
from pathlib import Path


def clip_starts(duration):
    if duration < 2:
        return []
    if duration < 4:
        return [(duration - 2) / 2]
    starts = [(duration - 2) / 4, 3 * (duration - 2) / 4]
    if starts[1] - starts[0] < 2:
        raise ValueError('approved quarter-position windows overlap for videos shorter than six seconds')
    return starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--limit', type=int, help='maximum source videos; for a small smoke run')
    parser.add_argument('--ffmpeg', default='ffmpeg', help='path to existing ffmpeg executable')
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError('output directory must be empty')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'proxies').mkdir()
    with args.manifest.open(encoding='utf-8', newline='') as stream:
        sources = list(csv.DictReader(stream))
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError('limit must be positive')
        sources = sources[:args.limit]
    items = []
    for row in sources:
        duration = float(row['duration'])
        for index, start in enumerate(clip_starts(duration)):
            relative = f"proxies/{row['source_id']}_{index}.mp4"
            subprocess.run([args.ffmpeg, '-nostdin', '-v', 'error', '-threads', '1', '-ss', str(start),
                            '-i', row['source_path'], '-t', '2', '-an', '-vf',
                            'scale=1280:720:force_original_aspect_ratio=decrease', '-c:v', 'libx264',
                            '-threads', '1', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                            str(args.out / relative)], check=True)
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
                if abs(actual_duration - 2) > 1 / fps + 0.001:
                    raise ValueError(f'incomplete proxy {relative}: {actual_duration}s')
            finally:
                capture.release()
            items.append({'path': relative, 'file': relative, 'source_id': row['source_id'],
                          'video': row['video'], 'start_sec': start, 'end_sec': start + 2,
                          'split': row['split'], 'domain': row['domain'], 'scenario': 'pilot',
                          'label_scope': 'any_pet_in_window', 'proxy_duration': actual_duration,
                          'review_status': 'unlabeled'})
    if not items:
        raise ValueError('no eligible clips')
    with (args.out / 'clips.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)
    (args.out / 'items.json').write_text(json.dumps({'count': len(items), 'items': items,
        'mode': 'video', 'hide_teacher': True, 'title': '视频标注 · 首轮',
        'description': '完整片段内出现过宠物即为有宠物'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'prepared {len(items)} clips from {len(sources)} sources')


if __name__ == '__main__':
    main()
