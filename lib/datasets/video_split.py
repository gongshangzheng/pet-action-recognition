"""Assign a versioned source-video inventory to shared dataset splits."""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from lib.datasets.interval_manifest import _path_parts
from lib.datasets.video_manifest import validate_records


def build_video_split(inventory_dir, output_dir, seed):
    inventory = Path(inventory_dir).resolve()
    try:
        inventory_data = (inventory / 'videos.jsonl').read_bytes()
        metadata_data = (inventory / 'manifest.json').read_bytes()
        metadata = json.loads(metadata_data)
        records = [json.loads(line) for line in inventory_data.splitlines()]
    except (OSError, ValueError) as error:
        raise ValueError(f'cannot read inventory {inventory}: {error}') from error
    digest = hashlib.sha256(inventory_data).hexdigest()
    if metadata.get('format_version') != 1 or metadata.get('count') != len(records) or metadata.get('videos_sha256') != digest:
        raise ValueError('inventory metadata mismatch')
    if not records:
        raise ValueError('empty inventory')
    validate_records(records)
    if any(row['video_id'] != row['path'] or _path_parts(row['path']) is None for row in records):
        raise ValueError('invalid inventory identity or path')
    ids = sorted(row['video_id'] for row in records)
    random.Random(seed).shuffle(ids)
    n = len(ids)
    train_count, val_count = n * 80 // 100, n * 10 // 100
    assignments = {video_id: ('train' if i < train_count else 'val' if i < train_count + val_count else 'test')
                   for i, video_id in enumerate(ids)}
    counts = {'train': train_count, 'val': val_count, 'test': n - train_count - val_count}
    result = {'metadata': {'format_version': 1, 'inventory_dir': str(inventory),
                           'inventory_sha256': digest,
                           'inventory_metadata_sha256': hashlib.sha256(metadata_data).hexdigest(),
                           'seed': seed, 'algorithm': 'sorted paths; random.Random(seed).shuffle; floor train and val',
                           'python_version': sys.version.split()[0],
                           'target_ratios': {'train': 0.8, 'val': 0.1, 'test': 0.1},
                           'counts': counts, 'actual_ratios': {k: v / n for k, v in counts.items()}},
              'videos': [{'video_id': video_id, 'split': assignments[video_id]} for video_id in sorted(ids)],
              'unassigned': []}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'split.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--seed', required=True, type=int)
    args = parser.parse_args()
    result = build_video_split(args.inventory_dir, args.output_dir, args.seed)
    print(json.dumps(result['metadata']['counts']))


if __name__ == '__main__':
    main()
