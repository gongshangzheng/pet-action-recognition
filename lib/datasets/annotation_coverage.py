"""Calculate nominal per-video annotation union and its complement."""

import argparse
import json
import sys
from pathlib import Path

from lib.datasets.interval_statistics import _positive_number, _sha256


def build_annotation_coverage(interval_statistics, video_statistics, output_dir):
    """Compute frame coverage, preserving errors and unmatched annotations."""
    interval_path, video_path = Path(interval_statistics).resolve(), Path(video_statistics).resolve()
    interval_bytes, video_bytes = interval_path.read_bytes(), video_path.read_bytes()
    intervals, videos = json.loads(interval_bytes), json.loads(video_bytes)
    imeta, vmeta = intervals['metadata'], videos['metadata']
    if imeta['format_version'] != 1 or vmeta['format_version'] != 1:
        raise ValueError('unsupported input format version')
    if imeta['video_statistics_sha256'] != _sha256(video_bytes):
        raise ValueError('video statistics hash mismatch')
    if imeta['inventory_sha256'] != vmeta['inventory_sha256'] or imeta['video_root'] != vmeta['video_root']:
        raise ValueError('inventory or source root mismatch')
    association_bytes = Path(imeta['interval_manifest_path']).read_bytes()
    if _sha256(association_bytes) != imeta['interval_manifest_sha256']:
        raise ValueError('interval manifest hash mismatch')
    association = json.loads(association_bytes)
    ameta = association['metadata']
    inventory = Path(ameta['inventory_dir'])
    manifest_bytes = (inventory / 'manifest.json').read_bytes()
    records_bytes = (inventory / 'videos.jsonl').read_bytes()
    invmeta = json.loads(manifest_bytes)
    if (_sha256(manifest_bytes) != ameta['inventory_metadata_sha256'] or
            _sha256(manifest_bytes) != vmeta['inventory_metadata_sha256'] or
            _sha256(records_bytes) != imeta['inventory_sha256'] or
            invmeta['video_root'] != imeta['video_root']):
        raise ValueError('inventory metadata or records mismatch')
    ids = [json.loads(line)['video_id'] for line in records_bytes.splitlines()]
    assoc_ids = [row['video_id'] for row in association['videos']]
    video_ids = [row['video_id'] for row in videos['videos']]
    if (len(set(ids)) != len(ids) or len(set(assoc_ids)) != len(assoc_ids) or
            len(set(video_ids)) != len(video_ids) or set(ids) != set(assoc_ids) or set(ids) != set(video_ids)):
        raise ValueError('inventory video identity mismatch')
    by_video = {video_id: [] for video_id in ids}
    for interval in intervals['intervals']:
        if interval['video_id'] not in by_video:
            raise ValueError('interval video not in inventory')
        by_video[interval['video_id']].append(interval)
    expected = {(video['video_id'], row['source_line']): row['fields']
                for video in association['videos'] for row in video['intervals']}
    actual = {(row['video_id'], row['source_line']): row['fields'] for row in intervals['intervals']}
    if len(expected) != len(intervals['intervals']) or expected != actual or association['unmatched'] != intervals['unmatched']:
        raise ValueError('interval rows do not match association')

    props = {row['video_id']: row for row in videos['videos']}
    results, errors = [], []
    for video_id in ids:
        rows = by_video[video_id]
        video = props[video_id]
        frame_count, fps = video['reported_frames'], video['fps']
        problems = []
        for row in rows:
            if row['reason']:
                problems.append({'video_id': video_id, 'source_line': row['source_line'], 'reason': row['reason']})
        if not _positive_number(frame_count) or not float(frame_count).is_integer():
            problems.append({'video_id': video_id, 'source_line': None, 'reason': 'invalid_reported_frames'})
        if not _positive_number(fps):
            problems.append({'video_id': video_id, 'source_line': None, 'reason': 'missing_fps'})
        errors.extend(problems)
        ranges = complement = union_frames = unannotated_frames = union_sec = unannotated_sec = None
        if not any(p['reason'] != 'missing_fps' for p in problems):
            count = int(frame_count)
            ranges = []
            for start, end in sorted((int(row['fields']['start_frame']), int(row['fields']['end_frame']) + 1)
                                     for row in rows):
                if ranges and start <= ranges[-1][1]:
                    ranges[-1][1] = max(ranges[-1][1], end)
                else:
                    ranges.append([start, end])
            complement = []
            previous = 0
            for start, end in ranges:
                if previous < start:
                    complement.append([previous, start])
                previous = end
            if previous < count:
                complement.append([previous, count])
            union_frames = sum(end - start for start, end in ranges)
            unannotated_frames = count - union_frames
            if _positive_number(fps):
                union_sec, unannotated_sec = union_frames / fps, unannotated_frames / fps
        results.append({'video_id': video_id, 'status': 'unknown' if problems else 'known',
                        'reasons': [p['reason'] for p in problems], 'reported_frames': frame_count,
                        'fps': fps, 'known_source_diagnostics': video.get('known_source_diagnostics', []),
                        'union_ranges': ranges, 'unannotated_ranges': complement,
                        'union_frames': union_frames, 'unannotated_frames': unannotated_frames,
                        'union_sec': union_sec, 'unannotated_sec': unannotated_sec})
    unmatched = intervals['unmatched']
    known = [row for row in results if row['status'] == 'known']
    summary = {'videos_total': len(results), 'known_videos': len(known),
               'unknown_videos': len(results) - len(known),
               'videos_without_annotations': sum(not by_video[video_id] for video_id in ids),
               'unmatched_count': len(unmatched), 'complete': not errors and not unmatched}
    for key in ('reported_frames', 'union_frames', 'unannotated_frames', 'union_sec', 'unannotated_sec'):
        summary[key] = sum(row[key] for row in known) if known else None
    result = {'metadata': {'format_version': 1, 'interval_statistics_path': str(interval_path),
                           'interval_statistics_sha256': _sha256(interval_bytes),
                           'video_statistics_path': str(video_path), 'video_statistics_sha256': _sha256(video_bytes),
                           'inventory_sha256': imeta['inventory_sha256'], 'video_root': imeta['video_root'],
                           'input_frame_convention': 'zero-based inclusive',
                           'output_ranges': 'zero-based half-open', 'duration_method': 'frames / reported_fps',
                           'summary_denominator': 'videos with known frame counts, valid intervals, and fps'},
              'videos': results, 'errors': errors, 'unmatched': unmatched, 'summary': summary}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'annotation_coverage.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval-statistics', type=Path, required=True)
    parser.add_argument('--video-statistics', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = build_annotation_coverage(args.interval_statistics, args.video_statistics, args.output_dir)
    root = Path(result['metadata']['video_root'])
    for error in result['errors']:
        line = f" line {error['source_line']}" if error['source_line'] is not None else ''
        print(f"ERROR {root / error['video_id']}{line}: {error['reason']}", file=sys.stderr)
    for row in result['unmatched']:
        print(f"ERROR {row['fields']['video']} line {row['source_line']}: {row['reason']}", file=sys.stderr)
    return 0 if result['summary']['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
