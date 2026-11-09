"""Associate raw interval CSV rows with a versioned video inventory."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from lib.datasets.video_manifest import validate_records


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _path_parts(value):
    parts = value.split('/')
    if not value or any(part in ('', '.', '..') for part in parts):
        return None
    return parts


def build_interval_manifest(inventory_dir, annotations, video_prefix, output_dir):
    """Preserve each raw CSV row and associate by explicit path prefix."""
    inventory_dir = Path(inventory_dir).resolve()
    annotations = Path(annotations).resolve()
    prefix = [] if video_prefix == '.' else _path_parts(video_prefix)
    if prefix is None:
        raise ValueError('invalid video prefix')

    inventory_bytes = (inventory_dir / 'videos.jsonl').read_bytes()
    metadata_bytes = (inventory_dir / 'manifest.json').read_bytes()
    inventory_meta = json.loads(metadata_bytes)
    records = [json.loads(line) for line in inventory_bytes.splitlines()]
    if (inventory_meta.get('format_version') != 1 or
            inventory_meta.get('videos_sha256') != _sha256(inventory_bytes) or
            inventory_meta.get('count') != len(records)):
        raise ValueError('inventory metadata mismatch')
    validate_records(records)
    if any(record['video_id'] != record['path'] or
           _path_parts(record['video_id']) is None for record in records):
        raise ValueError('invalid inventory identity or path')
    videos = [{'video_id': record['video_id'], 'intervals': []} for record in records]
    lookup = {item['video_id']: item['intervals'] for item in videos}

    annotation_bytes = annotations.read_bytes()
    reader = csv.reader(io.StringIO(annotation_bytes.decode('utf-8'), newline=''), strict=True)
    fields = next(reader, None)
    if not fields or 'video' not in fields or len(fields) != len(set(fields)):
        raise ValueError('annotation CSV must have unique headers including video')
    unmatched = []
    while True:
        line_number = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        if not values:
            continue
        if len(values) != len(fields):
            raise ValueError(f'malformed annotation CSV row at line {line_number}')
        row = dict(zip(fields, values, strict=True))
        interval = {'source_line': line_number, 'fields': row}
        parts = _path_parts(row['video'])
        if parts is None:
            reason = 'invalid_video_path'
        elif parts[:len(prefix)] != prefix or len(parts) <= len(prefix):
            reason = 'outside_video_prefix'
        else:
            video_id = '/'.join(parts[len(prefix):])
            if video_id in lookup:
                lookup[video_id].append(interval)
                continue
            reason = 'video_not_in_inventory'
        unmatched.append({**interval, 'reason': reason})

    result = {'metadata': {'format_version': 1, 'inventory_dir': str(inventory_dir),
                           'inventory_sha256': _sha256(inventory_bytes),
                           'inventory_metadata_sha256': _sha256(metadata_bytes),
                           'annotations_path': str(annotations),
                           'annotations_sha256': _sha256(annotation_bytes),
                           'video_prefix': video_prefix},
              'videos': videos, 'unmatched': unmatched}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'interval_manifest.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-dir', type=Path, required=True)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--video-prefix', required=True, help='CSV video path prefix; use . for none')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    build_interval_manifest(args.inventory_dir, args.annotations, args.video_prefix, args.output_dir)


if __name__ == '__main__':
    main()
