#!/usr/bin/env python3
"""Read-only Label Studio label counts; stdout only, no video access."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_ranges(spans):
    merged = []
    for start, end in sorted(set(spans)):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


class Counts:
    def __init__(self):
        self.raw = collections.Counter()
        self.pairs = set()
        self.meta = collections.Counter()

    def add(self, video, items):
        valid = False
        if not isinstance(items, list):
            self.meta['invalid_item_list'] += 1
            return False
        for item in items:
            if not isinstance(item, dict):
                self.meta['invalid_item'] += 1
                continue
            labels = item.get('timelinelabels', [])
            spans = item.get('ranges', [])
            if not isinstance(labels, list) or not isinstance(spans, list):
                self.meta['invalid_label_or_range_list'] += 1
                continue
            if not labels or not spans:
                self.meta['empty_label_or_range_items'] += 1
                continue
            if any(not isinstance(label, str) or not label.strip() for label in labels):
                self.meta['invalid_label'] += 1
                continue
            self.meta['behavior_items'] += 1
            self.meta['multi_label_items'] += int(len(set(labels)) > 1)
            for span in spans:
                if not isinstance(span, dict):
                    self.meta['invalid_range'] += 1
                    continue
                start, end = span.get('start'), span.get('end')
                if (isinstance(start, bool) or isinstance(end, bool)
                        or not isinstance(start, (int, float))
                        or not isinstance(end, (int, float))
                        or not float(start).is_integer() or not float(end).is_integer()
                        or start < 1 or end < start):
                    self.meta['invalid_range'] += 1
                    continue
                self.meta['range_occurrences'] += 1
                valid = True
                for label in labels:
                    self.raw[label] += 1
                    self.pairs.add((video, label, int(start), int(end)))
        return valid

    def report(self):
        grouped = collections.defaultdict(lambda: collections.defaultdict(list))
        for video, label, start, end in self.pairs:
            grouped[video][label].append((start, end))
        coverage = collections.Counter()
        exclusive = collections.Counter()
        class_overlap = collections.Counter()
        overlap_frames = overlap_videos = 0
        for labels in grouped.values():
            events = collections.defaultdict(collections.Counter)
            for label, spans in labels.items():
                for start, end in merge_ranges(spans):
                    coverage[label] += end - start + 1
                    events[start][label] += 1
                    events[end + 1][label] -= 1
            active = collections.Counter()
            previous = None
            video_overlap = False
            for frame, changes in sorted(events.items()):
                if previous is not None and frame > previous:
                    current = [label for label, count in active.items() if count > 0]
                    length = frame - previous
                    if len(current) == 1:
                        exclusive[current[0]] += length
                    elif len(current) > 1:
                        overlap_frames += length
                        video_overlap = True
                        for label in current:
                            class_overlap[label] += length
                active.update(changes)
                previous = frame
            overlap_videos += int(video_overlap)
        rows = []
        for label in sorted(self.raw):
            unique = [entry for entry in self.pairs if entry[1] == label]
            lengths = sorted(end - start + 1 for _, _, start, end in unique)
            rows.append(dict(label=label, raw_range_label_pairs=self.raw[label],
                             unique_ranges=len(unique),
                             distinct_videos=len({entry[0] for entry in unique}),
                             merged_covered_frames=coverage[label],
                             single_class_covered_frames=exclusive[label],
                             cross_class_overlap_frames=class_overlap[label],
                             min_range_frames=min(lengths),
                             median_range_frames=(lengths[(len(lengths)-1)//2]
                                                  + lengths[len(lengths)//2]) / 2,
                             max_range_frames=max(lengths)))
        return dict(counts=dict(self.meta), observed_classes=len(rows),
                    raw_range_label_pairs=sum(self.raw.values()),
                    unique_range_label_pairs=len(self.pairs),
                    labeled_distinct_videos=len(grouped),
                    cross_class_overlap_videos=overlap_videos,
                    cross_class_overlap_frames=overlap_frames, labels=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path('/home/work/analysis_code/datasets/company_video_paths')
    parser.add_argument('--csv', type=Path, default=root / 'merged_annotations.local.csv')
    parser.add_argument('--json', type=Path, default=root / 'merged_annotations.local.json')
    args = parser.parse_args()
    paths = [args.csv, args.json]
    before = {str(path): digest(path) for path in paths}
    csv_counts, json_counts = Counts(), Counts()
    with args.csv.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            csv_counts.meta['rows'] += 1
            behavior = json.loads(row.get('behavior') or '[]')
            if not csv_counts.add(row['video'], behavior):
                csv_counts.meta['rows_without_valid_ranges'] += 1
    tasks = json.loads(args.json.read_text(encoding='utf-8-sig'))
    if not isinstance(tasks, list):
        raise ValueError('Expected a JSON task list')
    result_types = collections.Counter()
    value_keys = collections.defaultdict(collections.Counter)
    for task in tasks:
        json_counts.meta['tasks'] += 1
        video = task['data']['video']
        annotations = task.get('annotations') or []
        json_counts.meta['tasks_with_multiple_annotations'] += int(len(annotations) > 1)
        valid = False
        for annotation in annotations:
            if annotation.get('was_cancelled', False):
                json_counts.meta['cancelled_annotations'] += 1
                continue
            json_counts.meta['non_cancelled_annotations'] += 1
            for result in annotation.get('result') or []:
                kind = str(result.get('type', 'missing'))
                result_types[kind] += 1
                value = result.get('value') or {}
                if not isinstance(value, dict):
                    json_counts.meta['invalid_result_value'] += 1
                    continue
                value_keys[kind].update(value.keys())
                if 'timelinelabels' in value or 'ranges' in value:
                    valid = json_counts.add(video, [value]) or valid
        if not valid:
            json_counts.meta['tasks_without_valid_ranges'] += 1
    after = {str(path): digest(path) for path in paths}
    if before != after:
        raise RuntimeError('Annotation input changed during the audit')
    report = dict(schema='company-action-label-audit-v1',
                  frame_convention='integer, one-based, inclusive; template not verified',
                  duration_seconds=None, video_files_opened=0, files_written=0,
                  input_sha256=before, input_sha256_unchanged=True,
                  csv=csv_counts.report(), json=json_counts.report(),
                  export_comparison=dict(
                      csv_only_range_label_pairs=len(csv_counts.pairs - json_counts.pairs),
                      json_only_range_label_pairs=len(json_counts.pairs - csv_counts.pairs)),
                  json_result_types=dict(result_types),
                  json_value_key_counts={key: dict(value) for key, value in value_keys.items()})
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
