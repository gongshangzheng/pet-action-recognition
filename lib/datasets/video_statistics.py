"""Measure nominal video duration from container properties, without decoding."""

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

from lib.datasets.interval_manifest import _path_parts
from lib.datasets.video_manifest import validate_records


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def build_video_statistics(inventory_dir, output_dir, quality_audit=None, audit_video_prefix=None):
    """Return per-video nominal duration and explicitly identified unknowns."""
    if (quality_audit is None) != (audit_video_prefix is None):
        raise ValueError('quality audit and audit video prefix must be provided together')
    prefix = [] if audit_video_prefix == '.' else _path_parts(audit_video_prefix) if audit_video_prefix is not None else []
    if prefix is None:
        raise ValueError('invalid audit video prefix')
    inventory = Path(inventory_dir).resolve()
    inventory_bytes = (inventory / 'videos.jsonl').read_bytes()
    metadata_bytes = (inventory / 'manifest.json').read_bytes()
    source_meta = json.loads(metadata_bytes)
    records = [json.loads(line) for line in inventory_bytes.splitlines()]
    if (source_meta.get('format_version') != 1 or source_meta.get('count') != len(records)
            or source_meta.get('videos_sha256') != _sha256(inventory_bytes)):
        raise ValueError('inventory metadata mismatch')
    validate_records(records)
    if any(row['video_id'] != row['path'] or _path_parts(row['path']) is None for row in records):
        raise ValueError('invalid inventory identity or path')
    root = Path(source_meta['video_root'])
    if not root.is_absolute():
        raise ValueError('invalid inventory video root')

    diagnostics = {row['video_id']: [] for row in records}
    unmatched = []
    audit_info = None
    if quality_audit is not None:
        audit_path = Path(quality_audit).resolve()
        audit_bytes = audit_path.read_bytes()
        audit = json.loads(audit_bytes)
        for item in audit['failed'] + audit['truncated']:
            parts = _path_parts(item['video'])
            if parts and parts[:len(prefix)] == prefix and len(parts) > len(prefix):
                video_id = '/'.join(parts[len(prefix):])
                if video_id in diagnostics:
                    diagnostics[video_id].append(item)
                    continue
            unmatched.append(item)
        audit_info = {'path': str(audit_path), 'sha256': _sha256(audit_bytes),
                      'video_prefix': audit_video_prefix, 'source_hashes_rechecked': False}

    import cv2

    rows = []
    durations = []
    for record in records:
        video_id = record['video_id']
        cap = cv2.VideoCapture(str(root / record['path']))
        fps = frames = duration = None
        reason = None
        try:
            if not cap.isOpened():
                reason = 'open_failed'
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if not math.isfinite(fps) or fps <= 0:
                    fps = None
                    reason = 'invalid_fps'
                if not math.isfinite(frames) or frames <= 0:
                    frames = None
                    reason = 'invalid_frame_count' if reason is None else 'invalid_fps_and_frame_count'
                if reason is None:
                    duration = frames / fps
                    durations.append(duration)
        finally:
            cap.release()
        rows.append({'video_id': video_id, 'status': 'unknown' if reason else 'known',
                     'fps': fps, 'reported_frames': frames, 'duration_sec': duration,
                     'reason': reason, 'known_source_diagnostics': diagnostics[video_id]})
    distribution = {'min': min(durations) if durations else None,
                    'max': max(durations) if durations else None,
                    'median': statistics.median(durations) if durations else None,
                    'mean': statistics.mean(durations) if durations else None,
                    'total': sum(durations) if durations else None}
    result = {'metadata': {'format_version': 1, 'inventory_dir': str(inventory),
                           'inventory_sha256': _sha256(inventory_bytes),
                           'inventory_metadata_sha256': _sha256(metadata_bytes),
                           'video_root': str(root), 'duration_method': 'reported_frames / fps',
                           'quality_audit': audit_info},
              'videos': rows, 'unmatched_quality_diagnostics': unmatched,
              'summary': {'videos_total': len(rows), 'known': len(durations),
                          'unknown': len(rows) - len(durations), 'duration_sec': distribution}}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'video_statistics.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--quality-audit', type=Path)
    parser.add_argument('--audit-video-prefix')
    args = parser.parse_args()
    result = build_video_statistics(args.inventory_dir, args.output_dir, args.quality_audit, args.audit_video_prefix)
    root = Path(result['metadata']['video_root'])
    for row in result['videos']:
        if row['reason']:
            print(f"ERROR {root / row['video_id']}: {row['reason']}", file=sys.stderr)
        for diagnostic in row['known_source_diagnostics']:
            if diagnostic.get('status') == 'source_decode_truncated':
                print(f"WARNING {root / row['video_id']}: historical decode truncation "
                      f"reported={diagnostic.get('reported')} decoded={diagnostic.get('decoded')}", file=sys.stderr)
            elif diagnostic.get('status') == 'source_unreadable':
                print(f"WARNING {root / row['video_id']}: historical source unreadable "
                      f"(not rechecked): {diagnostic.get('error')}", file=sys.stderr)
    return 1 if result['summary']['unknown'] else 0


if __name__ == '__main__':
    sys.exit(main())
