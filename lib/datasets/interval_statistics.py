"""Summarize original annotated interval rows using nominal video FPS."""

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _distribution(values):
    return {'total': sum(values) if values else None,
            'min': min(values) if values else None, 'max': max(values) if values else None,
            'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None}


def build_interval_statistics(interval_manifest, video_statistics, output_dir):
    """Preserve each original row, reporting invalid and unknown durations."""
    interval_path = Path(interval_manifest).resolve()
    video_path = Path(video_statistics).resolve()
    interval_bytes, video_bytes = interval_path.read_bytes(), video_path.read_bytes()
    association, video_stats = json.loads(interval_bytes), json.loads(video_bytes)
    a_meta, v_meta = association['metadata'], video_stats['metadata']
    for key in ('inventory_sha256', 'inventory_metadata_sha256'):
        if not a_meta.get(key) or a_meta[key] != v_meta.get(key):
            raise ValueError(f'inventory mismatch: {key}')
    if a_meta['format_version'] != 1 or v_meta['format_version'] != 1:
        raise ValueError('unsupported input format version')
    inventory = Path(a_meta['inventory_dir'])
    source_meta_bytes = (inventory / 'manifest.json').read_bytes()
    source_records = (inventory / 'videos.jsonl').read_bytes()
    source_meta = json.loads(source_meta_bytes)
    if (_sha256(source_meta_bytes) != a_meta['inventory_metadata_sha256'] or
            _sha256(source_records) != a_meta['inventory_sha256'] or
            source_meta['video_root'] != v_meta['video_root']):
        raise ValueError('inventory contents or video root mismatch')
    inventory_ids = [json.loads(line)['video_id'] for line in source_records.splitlines()]
    association_ids = [item['video_id'] for item in association['videos']]
    video_ids = [item['video_id'] for item in video_stats['videos']]
    if (len(set(inventory_ids)) != len(inventory_ids) or len(set(association_ids)) != len(association_ids)
            or len(set(video_ids)) != len(video_ids) or set(inventory_ids) != set(association_ids)
            or set(inventory_ids) != set(video_ids)):
        raise ValueError('inventory video identity mismatch')
    video_lookup = {item['video_id']: item for item in video_stats['videos']}
    rows, grouped = [], {}
    for video in association['videos']:
        video_id = video['video_id']
        props = video_lookup[video_id]
        for interval in video['intervals']:
            fields = interval['fields']
            label = fields['label']
            row = {'video_id': video_id, 'source_line': interval['source_line'], 'fields': fields,
                   'status': 'known', 'reason': None, 'frame_count': None, 'duration_sec': None}
            try:
                start, end = int(fields['start_frame']), int(fields['end_frame'])
                if start < 0 or end < start:
                    raise ValueError
            except (ValueError, TypeError):
                row.update(status='invalid', reason='invalid_frame_range')
            else:
                frame_count = end - start + 1
                frames, fps = props['reported_frames'], props['fps']
                if _positive_number(frames) and end >= frames:
                    row.update(status='invalid', reason='end_out_of_bounds')
                else:
                    row['frame_count'] = frame_count
                    if not _positive_number(frames):
                        row.update(status='unknown', reason='missing_reported_frames')
                    elif not _positive_number(fps):
                        row.update(status='unknown', reason='missing_fps')
                    else:
                        row['duration_sec'] = frame_count / fps
            rows.append(row)
            grouped.setdefault(label, []).append(row)
    labels = {}
    for label, items in sorted(grouped.items()):
        durations = [item['duration_sec'] for item in items if item['duration_sec'] is not None]
        frames = [item['frame_count'] for item in items if item['frame_count'] is not None]
        labels[label] = {'interval_count': len(items), 'video_count': len({item['video_id'] for item in items}),
                         'total_frames': sum(frames) if frames else None,
                         'duration_known': len(durations), 'duration_unknown': len(items) - len(durations),
                         'duration_sec': _distribution(durations)}
    unmatched = association['unmatched']
    result = {'metadata': {'format_version': 1, 'interval_manifest_path': str(interval_path),
                           'interval_manifest_sha256': _sha256(interval_bytes),
                           'video_statistics_path': str(video_path), 'video_statistics_sha256': _sha256(video_bytes),
                           'inventory_sha256': a_meta['inventory_sha256'], 'video_root': v_meta['video_root'],
                           'frame_convention': 'zero-based inclusive', 'duration_method': 'frame_count / reported_fps',
                           'statistics_unit': 'one original CSV row; overlaps and duplicates retained'},
              'intervals': rows, 'unmatched': unmatched, 'labels': labels,
              'summary': {'videos_total': len(association_ids),
                          'videos_without_intervals': sum(not item['intervals'] for item in association['videos']),
                          'unmatched_count': len(unmatched), 'intervals_total': len(rows),
                          'duration_known': sum(row['status'] == 'known' for row in rows),
                          'duration_unknown': sum(row['status'] != 'known' for row in rows)}}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'interval_statistics.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval-manifest', type=Path, required=True)
    parser.add_argument('--video-statistics', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = build_interval_statistics(args.interval_manifest, args.video_statistics, args.output_dir)
    root = Path(result['metadata']['video_root'])
    for row in result['intervals']:
        if row['reason']:
            print(f"ERROR {root / row['video_id']} line {row['source_line']}: {row['reason']}", file=sys.stderr)
    for row in result['unmatched']:
        print(f"ERROR {row['fields']['video']} line {row['source_line']}: {row['reason']}", file=sys.stderr)
    return 1 if result['summary']['duration_unknown'] or result['unmatched'] else 0


if __name__ == '__main__':
    sys.exit(main())
