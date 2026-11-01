#!/usr/bin/env python3
"""Normalize mixed timestamp schemas in a gate video review set."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--set', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    args = parser.parse_args()

    with args.manifest.open(encoding='utf-8', newline='') as stream:
        source_fps = {row['video']: float(row['fps']) for row in csv.DictReader(stream)}
    if len(source_fps) != len(set(source_fps)):
        raise ValueError('source manifest contains duplicate videos')

    items_path = args.set / 'items.json'
    progress_path = args.set / 'progress.jsonl'
    clips_path = args.set / 'clips.csv'
    before = {path.name: digest(path) for path in (items_path, progress_path, clips_path)}
    data = json.loads(items_path.read_text(encoding='utf-8'))
    changed = 0
    for item in data['items']:
        fps = source_fps.get(item['video'])
        if not fps or fps <= 0:
            raise ValueError(f"missing source fps: {item['video']}")
        normalized = []
        old_fields = {'decoded_sec', 'delta_sec'}
        for frame_id, sample in zip(item['frame_ids'], item['sample_timestamps']):
            frame_sec = frame_id / fps
            if old_fields.intersection(sample):
                container_sec = float(sample['decoded_sec'])
            else:
                container_sec = float(sample['container_sec'])
                if abs(float(sample['frame_sec']) - frame_sec) > 1e-9:
                    raise ValueError(f"frame timestamp mismatch: {item['path']} frame {frame_id}")
            normalized.append({
                'target_sec': float(sample['target_sec']),
                'frame_sec': frame_sec,
                'container_sec': container_sec,
                'container_minus_frame_sec': container_sec - frame_sec,
            })
        if len(normalized) != 4:
            raise ValueError(f"invalid sample count: {item['path']}")
        if normalized != item['sample_timestamps']:
            changed += 1
        item['sample_timestamps'] = normalized

    temporary = items_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, items_path)

    by_path = {item['path']: item for item in data['items']}
    with progress_path.open(encoding='utf-8') as stream:
        progress = [json.loads(line) for line in stream if line.strip()]
    if len(progress) != len(data['items']):
        raise ValueError('progress and items counts differ')
    with progress_path.open('w', encoding='utf-8') as stream:
        for record in progress:
            if record['path'] not in by_path:
                raise ValueError(f"unknown progress path: {record['path']}")
            stream.write(json.dumps(by_path[record['path']], ensure_ascii=False) + '\n')

    with clips_path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    fieldnames = list(rows[0])
    for row in rows:
        row['sample_timestamps'] = json.dumps(by_path[row['path']]['sample_timestamps'],
                                               ensure_ascii=False)
    temporary = clips_path.with_suffix('.csv.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, clips_path)

    after = {path.name: digest(path) for path in (items_path, progress_path, clips_path)}
    audit = {'changed_items': changed, 'total_items': len(data['items']),
             'before_sha256': before, 'after_sha256': after}
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.audit.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, args.audit)
    print(f"normalized {changed} items; verified {len(data['items'])}")
    return 0


if __name__ == '__main__':
    main()
