"""List same-label and different-label overlaps between original annotation rows."""

import argparse
import itertools
import json
import sys
from pathlib import Path

from lib.datasets.interval_statistics import _sha256


def build_annotation_overlaps(interval_statistics, output_dir):
    """Preserve overlapping pairs and pending rows without adjudicating labels."""
    source = Path(interval_statistics).resolve()
    data = source.read_bytes()
    stats = json.loads(data)
    metadata = stats['metadata']
    if metadata['format_version'] != 1 or metadata['frame_convention'] != 'zero-based inclusive':
        raise ValueError('unsupported interval statistics version or frame convention')

    grouped, errors = {}, []
    for row in stats['intervals']:
        if row['reason']:
            errors.append(row)
        if row['status'] == 'invalid':
            continue
        start, end = int(row['fields']['start_frame']), int(row['fields']['end_frame'])
        if start < 0 or end < start:
            raise ValueError(f"invalid frame range at line {row['source_line']}")
        grouped.setdefault(row['video_id'], []).append(row)

    pairs, affected = [], {}
    for video_id, rows in grouped.items():
        for left, right in itertools.combinations(sorted(rows, key=lambda row: row['source_line']), 2):
            start = max(int(left['fields']['start_frame']), int(right['fields']['start_frame']))
            end = min(int(left['fields']['end_frame']), int(right['fields']['end_frame']))
            if start > end:
                continue
            kind = 'same_label' if left['fields']['label'] == right['fields']['label'] else 'different_label'
            pairs.append({'video_id': video_id, 'kind': kind, 'left': left, 'right': right,
                          'intersection': {'start_frame': start, 'end_frame': end, 'frame_count': end - start + 1}})
            for row in (left, right):
                affected[video_id, row['source_line']] = {**row, 'review_status': 'pending'}

    summary = {}
    for kind in ('same_label', 'different_label'):
        selected = [pair for pair in pairs if pair['kind'] == kind]
        summary[kind] = {'pair_count': len(selected), 'video_count': len({p['video_id'] for p in selected})}
    unmatched = stats['unmatched']
    summary.update(affected_interval_count=len(affected),
                   affected_video_count=len({key[0] for key in affected}),
                   error_count=len(errors), unmatched_count=len(unmatched), complete=not errors and not unmatched)
    result = {'metadata': {'format_version': 1, 'interval_statistics_path': str(source),
                           'interval_statistics_sha256': _sha256(data), 'video_root': metadata['video_root'],
                           'frame_convention': 'zero-based inclusive',
                           'statistics_unit': 'one unordered pair of original rows within one video',
                           'label_comparison': 'exact original label string equality',
                           'scope': 'annotation frame intersections, not animal or action attribution'},
              'pairs': pairs, 'affected_intervals': [affected[key] for key in sorted(affected)],
              'errors': errors, 'unmatched': unmatched, 'summary': summary}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'annotation_overlaps.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval-statistics', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = build_annotation_overlaps(args.interval_statistics, args.output_dir)
    root = Path(result['metadata']['video_root'])
    for row in result['errors']:
        print(f"ERROR {root / row['video_id']} line {row['source_line']}: {row['reason']}", file=sys.stderr)
    for row in result['unmatched']:
        print(f"ERROR {row['fields']['video']} line {row['source_line']}: {row['reason']}", file=sys.stderr)
    return 0 if result['summary']['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
