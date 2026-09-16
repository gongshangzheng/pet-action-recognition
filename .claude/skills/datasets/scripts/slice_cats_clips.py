#!/usr/bin/env python3
"""Cats 视频切段脚本 — 4s clip, stride=2s, 按重叠帧数投票分配标签。

用法：
    python3 scripts/slice_cats_clips.py --root /home/wyy/mnt/cats --output /home/wyy/mnt/cats/quadruped_cats_v1
    python3 scripts/slice_cats_clips.py --root /home/wyy/mnt/cats --output /home/wyy/mnt/cats/quadruped_cats_v1 \
        --clip-length 4 --stride 2 --fps 15

输入：
    --root/dataset_崔/      mp4 视频（hash 前缀已剥离）
    --root/dataset_蒋/      mp4 视频（hash 前缀已剥离）
    --root/annotation_崔/    project-8 JSON + CSV
    --root/annotation_蒋/    project-6 JSON + CSV

输出：
    <output>/
    ├── classes.txt
    ├── videos/                  所有 clip mp4
    └── annotation/
        ├── train_public.txt
        ├── val_public.txt
        └── test_public.txt
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import cv2


LABEL_MAP = {
    "common/activity": 0,
    "common/drinking": 1,
    "common/eating": 2,
    "common/grooming": 3,
    "common/prolonged_stationary": 4,
}
LABEL_NAMES = ["activity", "drinking", "eating", "grooming", "prolonged_stationary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Slice cats videos into clips with label assignment.")
    parser.add_argument("--root", required=True, help="Root dir containing dataset_崔/, dataset_蒋/, annotation_崔/, annotation_蒋/")
    parser.add_argument("--output", required=True, help="Output directory for sliced dataset")
    parser.add_argument("--clip-length", type=float, default=4.0, help="Clip length in seconds (default: 4)")
    parser.add_argument("--stride", type=float, default=2.0, help="Stride in seconds (default: 2)")
    parser.add_argument("--fps", type=float, default=15.0, help="Video FPS (default: 15)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Val split ratio")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    return parser.parse_args()


def load_annotations(root: str) -> dict[str, list[tuple[int, int, str]]]:
    """Load all annotations from JSON files.
    Returns: {event_fname: [(ann_start_frame, ann_end_frame, label), ...]}
    """
    annotations: dict[str, list[tuple[int, int, str]]] = defaultdict(list)

    for sub in os.listdir(root):
        if not sub.startswith("annotation_"):
            continue
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue

        json_files = [f for f in os.listdir(sub_path) if f.endswith(".json")]
        for json_file in json_files:
            json_path = os.path.join(sub_path, json_file)
            with open(json_path, encoding="utf-8") as f:
                items = json.load(f)

            for item in items:
                data = item.get("data", {})
                video_path = data.get("video", "")
                if not video_path:
                    continue
                # Extract event filename: HASH-event_TS.mp4 -> event_TS.mp4
                fname = os.path.basename(video_path)  # HASH-event_TS.mp4
                parts = fname.split("-", 1)
                if len(parts) < 2:
                    continue
                event_fname = parts[1]  # event_TS.mp4

                for ann in item.get("annotations", []):
                    for res in ann.get("result", []):
                        val = res.get("value", {})
                        ranges = val.get("ranges", [])
                        labels = val.get("timelinelabels", [])
                        for rng in ranges:
                            for lbl in labels:
                                # lbl format: "common/drinking"
                                if lbl not in LABEL_MAP:
                                    continue
                                ann_start = int(rng["start"])
                                ann_end = int(rng["end"])
                                annotations[event_fname].append((ann_start, ann_end, lbl))

    return annotations


def slice_video(
    video_path: str,
    event_fname: str,
    annotations: list[tuple[int, int, str]],
    clip_len_frames: int,
    stride_frames: int,
    fps: float,
) -> list[tuple[str, int, int, int]]:
    """Slice one video into clips with label assignment.

    Returns: [(clip_fname, clip_start_frame, clip_end_frame, label_int), ...]
    """
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    clips = []
    clip_idx = 0
    clip_start = 0

    while clip_start < total_frames:
        clip_end = min(clip_start + clip_len_frames, total_frames)

        # Overlap voting: sum overlap frames per label
        overlap_per_label: Counter = Counter()
        for ann_start, ann_end, lbl in annotations:
            overlap_start = max(clip_start, ann_start)
            overlap_end = min(clip_end, ann_end)
            overlap_len = overlap_end - overlap_start
            if overlap_len > 0:
                overlap_per_label[lbl] += overlap_len

        if overlap_per_label:
            primary_label = overlap_per_label.most_common(1)[0][0]
            label_int = LABEL_MAP[primary_label]
        else:
            label_int = -1  # no label

        # Build clip filename
        # event_20260806_120311.mp4 -> event_20260806_120311_0001.mp4
        name_part = event_fname.replace(".mp4", "")
        clip_fname = f"{name_part}_{clip_idx+1:04d}.mp4"

        clips.append((clip_fname, clip_start, clip_end, label_int))

        clip_start += stride_frames
        clip_idx += 1

    return clips


def build_videos_index(root: str) -> dict[str, str]:
    """Build {event_fname: full_path} for all videos in dataset_崔/ and dataset_蒋/."""
    index: dict[str, str] = {}
    for sub in os.listdir(root):
        if not sub.startswith("dataset_"):
            continue
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue
        for fname in os.listdir(sub_path):
            if fname.endswith(".mp4"):
                index[fname] = os.path.join(sub_path, fname)
    return index


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output = Path(args.output)

    random.seed(args.seed)

    # Load annotations
    print("Loading annotations...")
    annotations = load_annotations(str(root))
    print(f"  {len(annotations)} videos with annotations")

    # Build video index
    print("Indexing videos...")
    video_index = build_videos_index(str(root))
    print(f"  {len(video_index)} total videos")

    # Stats
    label_counter = Counter()
    clip_counter = Counter()
    total_clips = 0
    labeled_clips = 0

    # For splitting: collect per-video clips info
    video_splits: list[tuple[str, str, list[tuple]]] = []  # (event_fname, split, clips)

    # Split videos: stratified by label distribution
    labeled_videos = [
        (vf, anns) for vf, anns in annotations.items() if vf in video_index
    ]
    unlabeled_videos = [
        (vf, []) for vf in video_index if vf not in annotations
    ]

    # Sort by primary label for stratification
    labeled_videos.sort(key=lambda x: x[0])
    random.shuffle(labeled_videos)

    n_labeled = len(labeled_videos)
    n_train = int(n_labeled * args.train_ratio)
    n_val = int(n_labeled * args.val_ratio)

    splits_assign: dict[str, str] = {}
    for i, (vf, anns) in enumerate(labeled_videos):
        if i < n_train:
            split = "train"
        elif i < n_train + n_val:
            split = "val"
        else:
            split = "test"
        splits_assign[vf] = split

    # Process each labeled video
    clip_len_frames = int(args.clip_length * args.fps)
    stride_frames = int(args.stride * args.fps)

    all_clips: list[tuple[str, str, int]] = []  # (clip_fname, split, label_int)

    print(f"\nSlicing with clip_len={args.clip_length}s, stride={args.stride}s, fps={args.fps}...")

    for event_fname, anns in labeled_videos:
        video_path = video_index[event_fname]
        split = splits_assign[event_fname]

        clips = slice_video(
            video_path, event_fname, anns,
            clip_len_frames, stride_frames, args.fps
        )

        for clip_fname, _, _, label_int in clips:
            if label_int >= 0:
                all_clips.append((clip_fname, split, label_int))
                label_counter[LABEL_MAP_REVERSE[label_int]] += 1

        clip_counter[split] += len(clips)
        total_clips += len(clips)

    print(f"  Total clips generated: {total_clips}")
    print(f"  Labeled clips: {len(all_clips)}")
    print(f"  Per split: train={clip_counter['train']}, val={clip_counter['val']}, test={clip_counter['test']}")
    print(f"\nLabel distribution (labeled clips):")
    for lbl_name, count in sorted(label_counter.items(), key=lambda x: -x[1]):
        print(f"  {lbl_name}: {count}")

    # Write output
    if args.dry_run:
        print("\n[dry-run] Skipping file writes")
        return

    print(f"\nWriting to {output}...")
    videos_dir = output / "videos"
    ann_dir = output / "annotation"
    videos_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    # Write classes.txt
    with open(output / "classes.txt", "w", encoding="utf-8") as f:
        for name in LABEL_NAMES:
            f.write(name + "\n")
    print(f"  Wrote classes.txt")

    # Write annotation files
    for split in ["train", "val", "test"]:
        split_clips = [(cf, li) for cf, s, li in all_clips if s == split]
        with open(ann_dir / f"{split}_public.txt", "w", encoding="utf-8") as f:
            for clip_fname, label_int in split_clips:
                # path relative to data_prefix.video (which will be set to output dir)
                f.write(f"videos/{clip_fname} {label_int}\n")
        print(f"  Wrote {split}_public.txt ({len(split_clips)} clips)")

    # Copy all videos and extract clips
    print("\nExtracting clips (this may take a while)...")
    clip_paths: dict[str, Path] = {}

    # Group clips by parent video
    video_clips: dict[str, list[tuple[str, int, int, int]]] = defaultdict(list)
    for event_fname, anns in labeled_videos:
        video_path = video_index[event_fname]
        clips = slice_video(
            video_path, event_fname, anns,
            clip_len_frames, stride_frames, args.fps
        )
        video_clips[event_fname] = clips

    for event_fname, clips in video_clips.items():
        video_path = video_index[event_fname]
        cap = cv2.VideoCapture(video_path)

        for clip_fname, clip_start, clip_end, label_int in clips:
            if label_int < 0:
                continue

            clip_path = videos_dir / clip_fname
            clip_paths[clip_fname] = clip_path

            if clip_path.exists():
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, clip_start)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(
                str(clip_path), fourcc, args.fps,
                (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            )

            frame_idx = clip_start
            while frame_idx < clip_end:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                frame_idx += 1

            out.release()

        cap.release()

    print(f"  Extracted {len(clip_paths)} labeled clips to {videos_dir}")

    # Summary JSON
    summary = {
        "source": "cats",
        "clip_length_s": args.clip_length,
        "stride_s": args.stride,
        "fps": args.fps,
        "total_clips": len(all_clips),
        "split_counts": {
            split: len([1 for _, s, _ in all_clips if s == split])
            for split in ["train", "val", "test"]
        },
        "label_counts": dict(label_counter),
        "label_names": LABEL_NAMES,
        "seed": args.seed,
    }
    with open(output / "slice_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nDone! Summary written to {output}/slice_summary.json")


# Reverse map for convenience
LABEL_MAP_REVERSE = {v: k for k, v in LABEL_MAP.items()}


if __name__ == "__main__":
    main()
