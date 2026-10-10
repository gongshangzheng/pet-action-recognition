#!/usr/bin/env python3
"""Read-only sample of media stream metadata; no decoding or saved outputs."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(path):
    info = path.stat()
    return info.st_size, info.st_mtime_ns, info.st_ino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=Path(
        '/home/work/analysis_code/datasets/company_video_paths/merged_annotations.local.csv'))
    parser.add_argument('--video-root', type=Path,
                        default=Path('/home/work/pet_analysis_wyy/dataset-wyy'))
    parser.add_argument('--samples', type=int, default=12)
    parser.add_argument('--seed', type=int, default=20261010)
    args = parser.parse_args()
    if not 1 <= args.samples <= 100:
        parser.error('--samples must be 1..100')
    before = digest(args.csv)
    root = args.video_root.resolve(strict=True)
    groups = collections.defaultdict(set)
    all_paths = set()
    with args.csv.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            path = Path(row['video']).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError('Video outside the expected root or not a file')
            all_paths.add(path)
            for item in json.loads(row.get('behavior') or '[]'):
                for label in item.get('timelinelabels', []):
                    groups[label].add(path)
    rng = random.Random(args.seed)
    selected = []
    used = set()
    for label in sorted(groups):
        candidates = sorted(groups[label] - used)
        if candidates and len(selected) < args.samples:
            path = rng.choice(candidates)
            selected.append((path, label))
            used.add(path)
    remaining = sorted(all_paths - used)
    rng.shuffle(remaining)
    for path in remaining[:args.samples - len(selected)]:
        selected.append((path, 'random_fill'))
    import av
    records = []
    for path, label in selected:
        initial = state(path)
        record = dict(sample_id=hashlib.sha256(str(path).encode()).hexdigest()[:16],
                      selected_for=label)
        try:
            with av.open(str(path), mode='r') as container:
                audio = list(container.streams.audio)
                video = list(container.streams.video)
                record.update(status='ok', stream_count=len(container.streams),
                              audio_streams=len(audio), video_streams=len(video),
                              duration_seconds=(container.duration / av.time_base
                                                if container.duration is not None else None))
                record['video'] = [dict(codec=s.codec_context.name,
                                       width=s.codec_context.width,
                                       height=s.codec_context.height,
                                       average_fps=float(s.average_rate)
                                       if s.average_rate is not None else None)
                                   for s in video]
                record['audio'] = [dict(codec=s.codec_context.name,
                                       sample_rate=s.codec_context.sample_rate,
                                       channels=len(s.codec_context.layout.channels))
                                   for s in audio]
        except Exception as exc:
            record.update(status='error', error_type=type(exc).__name__)
        if initial != state(path):
            raise RuntimeError('Sample metadata changed during the probe')
        records.append(record)
    if before != digest(args.csv):
        raise RuntimeError('CSV changed during the probe')
    ok = [row for row in records if row['status'] == 'ok']
    report = dict(schema='company-video-audio-sample-v1',
                  strategy='one different video per observed label, then random fill',
                  seed=args.seed, requested_samples=args.samples,
                  sample_count=len(records), successful_samples=len(ok),
                  failed_samples=len(records) - len(ok),
                  samples_with_audio=sum(row['audio_streams'] > 0 for row in ok),
                  audio_streams_total=sum(row['audio_streams'] for row in ok),
                  csv_sha256=before, input_states_unchanged=True,
                  probe_backend='PyAV ' + av.__version__,
                  decode_calls=0, demux_calls=0, files_written=0, records=records)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
