#!/usr/bin/env python3
"""Prepare paired raw, GroundingDINO crop and pixel-assisted cat datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from petlib.datasets.cat_crop import (  # noqa: E402
    build_frame_track,
    classify_frame,
    crop_square,
    interval_status,
    letterbox_square,
    motion_correct_box,
)
from petlib.videowriter import H264VideoWriter  # noqa: E402


CLASSES = [
    "activity",
    "eating",
    "drinking",
    "prolonged_stationary",
    "grooming",
    "toileting",
    "abnormal",
]
ARMS = ("raw", "gdino", "gdino_motion")
CACHE_SCHEMA = "cat-crop-detection-v2"
DEFAULT_RUN_ROOT = ROOT / "results/cat_crop_classification/gdino-crop-20261103a"
DEFAULT_DATASET_ID = "gdino-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def source_records(
    index_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    rows: list[dict[str, Any]] = []
    splits_by_video: dict[str, list[str]] = defaultdict(list)
    for split in ("train", "val", "test"):
        for row in read_jsonl(index_root / f"{split}.jsonl"):
            enriched = dict(row)
            enriched["split"] = split
            rows.append(enriched)
            if split not in splits_by_video[row["video"]]:
                splits_by_video[row["video"]].append(split)
    return rows, dict(splits_by_video)


def selected_videos(
    splits_by_video: dict[str, list[str]],
    requested: list[str],
    max_videos: int | None,
) -> list[str]:
    videos = sorted(splits_by_video)
    if requested:
        names = {Path(value).name for value in requested}
        videos = [
            video for video in videos if video in requested or Path(video).name in names
        ]
        missing = sorted(names - {Path(video).name for video in videos})
        if missing:
            raise ValueError(
                f"Requested videos are absent from source index: {missing}"
            )
    if max_videos is not None:
        if max_videos < 1:
            raise ValueError("--max-videos must be positive")
        videos = videos[:max_videos]
    return videos


def cache_paths(asset_root: Path, video: str) -> dict[str, Path]:
    stem = Path(video).stem
    return {
        "detection": asset_root / "detections" / f"{stem}.json",
        "metadata": asset_root / "metadata" / f"{stem}.json",
        "gdino": asset_root / "videos/gdino" / f"{stem}.mp4",
        "gdino_motion": asset_root / "videos/gdino_motion" / f"{stem}.mp4",
    }


def load_reusable_detection(
    path: Path,
    video_path: Path,
    source_hash: str,
    fingerprint: dict[str, Any],
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != CACHE_SCHEMA:
        raise RuntimeError(f"Detection cache schema mismatch: {path}")
    if data.get("source_path") != str(video_path):
        raise RuntimeError(f"Detection cache source path mismatch: {path}")
    if data.get("source_sha256") != source_hash:
        raise RuntimeError(f"Detection cache source hash mismatch: {path}")
    if data.get("fingerprint") != fingerprint:
        raise RuntimeError(f"Detection cache settings mismatch: {path}")
    return data


def read_source_properties(path: Path) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    props = {
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "frame_count_reported": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    cap.release()
    if props["fps"] <= 0 or props["width"] <= 0 or props["height"] <= 0:
        raise RuntimeError(f"Invalid source video properties: {path}: {props}")
    return props


def build_detector(args: argparse.Namespace):
    model_dir = Path(args.model_dir).expanduser()
    if not (model_dir / "config.json").is_file():
        raise FileNotFoundError(
            f"GroundingDINO model directory is incomplete: {model_dir}"
        )
    import torch
    from petlib.detection.grounding_dino import GroundingDinoDetector

    torch.set_num_threads(args.torch_threads)
    torch.set_num_interop_threads(1)
    detector = GroundingDinoDetector(
        model_dir=str(model_dir),
        box_threshold=args.threshold,
        text_threshold=args.text_threshold,
        device=args.device,
    )
    return detector


def model_fingerprint(model_dir: Path) -> dict[str, Any]:
    weights = model_dir / "model.safetensors"
    config = model_dir / "config.json"
    if not weights.is_file() or not config.is_file():
        raise FileNotFoundError(f"Incomplete GroundingDINO model: {model_dir}")
    return {
        "path": str(model_dir),
        "weights_sha256": sha256(weights),
        "weights_bytes": weights.stat().st_size,
        "config_sha256": sha256(config),
    }


def detect_video(
    video: str,
    video_root: Path,
    asset_root: Path,
    detector,
    fingerprint: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    source = video_root / video
    if not source.is_file():
        raise FileNotFoundError(source)
    output = cache_paths(asset_root, video)["detection"]
    source_hash = sha256(source)
    reusable = load_reusable_detection(output, source, source_hash, fingerprint)
    if reusable is not None and not args.force:
        reusable["reused"] = True
        return reusable

    props = read_source_properties(source)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {source}")
    anchors: dict[int, dict[str, Any]] = {}
    frame_index = 0
    sampled_frames = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if frame_index % args.sample_stride:
            frame_index += 1
            continue
        ok, frame = cap.retrieve()
        if not ok:
            cap.release()
            raise RuntimeError(f"Cannot decode sampled frame {frame_index}: {source}")
        detections = detector.detect(frame, classes=("cat", "dog"))
        serialized = [
            {
                "class": detection.cls,
                "box": [float(value) for value in detection.box],
                "confidence": float(detection.conf),
            }
            for detection in detections
        ]
        anchors[frame_index] = classify_frame(
            serialized, props["width"], props["height"]
        )
        sampled_frames += 1
        if sampled_frames % 50 == 0:
            print(
                f"[detect] {Path(video).name}: {sampled_frames} samples "
                f"through frame {frame_index}",
                flush=True,
            )
        frame_index += 1
    cap.release()
    if frame_index == 0:
        raise RuntimeError(f"Video has no decoded frames: {source}")

    reason_counts = Counter(
        reason for state in anchors.values() for reason in state["reasons"]
    )
    payload = {
        "schema": CACHE_SCHEMA,
        "status": "complete",
        "created_utc": utc_now(),
        "source_path": str(source),
        "source_sha256": source_hash,
        "source_bytes": source.stat().st_size,
        "video": video,
        "properties": props,
        "decoded_frames": frame_index,
        "sampled_frames": sampled_frames,
        "fingerprint": fingerprint,
        "sample_stride": args.sample_stride,
        "box_threshold": args.threshold,
        "text_threshold": args.text_threshold,
        "classes": ["cat", "dog"],
        "reason_counts": dict(reason_counts),
        "anchors": {str(frame): state for frame, state in sorted(anchors.items())},
        "reused": False,
    }
    atomic_json(output, payload)
    print(
        f"[detect] {Path(video).name}: {frame_index} frames, "
        f"{sampled_frames} samples, reasons={dict(reason_counts)}",
        flush=True,
    )
    return payload


def load_detection(asset_root: Path, video: str) -> dict[str, Any]:
    path = cache_paths(asset_root, video)["detection"]
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "complete":
        raise RuntimeError(f"Detection is incomplete: {path}")
    return data


def render_video(
    video: str,
    video_root: Path,
    asset_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source = video_root / video
    detection = load_detection(asset_root, video)
    paths = cache_paths(asset_root, video)
    if (
        paths["gdino"].is_file()
        and paths["gdino_motion"].is_file()
        and paths["metadata"].is_file()
        and not args.force
    ):
        metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        if (
            metadata.get("source_sha256") == detection["source_sha256"]
            and metadata.get("detection_fingerprint") == detection["fingerprint"]
            and metadata.get("render_fingerprint") == render_fingerprint(args)
        ):
            metadata["reused"] = True
            return metadata
        raise RuntimeError(
            "Existing crop outputs do not match the source or render settings; "
            f"use a new asset root or pass --force deliberately: {paths['metadata']}"
        )

    anchors = {int(frame): state for frame, state in detection["anchors"].items()}
    track = build_frame_track(
        anchors,
        int(detection["decoded_frames"]),
        args.sample_stride,
        args.max_gap,
    )
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {source}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    bg = cv2.createBackgroundSubtractorMOG2(
        history=120, varThreshold=25, detectShadows=False
    )
    previous_hit = False
    frame_index = 0
    invalid_frames = 0
    display_box_frames = 0
    letterbox_frames = 0
    corrected_frames = 0
    paths["gdino"].parent.mkdir(parents=True, exist_ok=True)
    paths["gdino_motion"].parent.mkdir(parents=True, exist_ok=True)
    temporary_gdino = paths["gdino"].with_suffix(".mp4.writing.mp4")
    temporary_motion = paths["gdino_motion"].with_suffix(".mp4.writing.mp4")
    with (
        H264VideoWriter(
            str(temporary_gdino),
            fps,
            (args.size, args.size),
            crf=args.crf,
            threads=args.ffmpeg_threads,
        ) as gdino_writer,
        H264VideoWriter(
            str(temporary_motion),
            fps,
            (args.size, args.size),
            crf=args.crf,
            threads=args.ffmpeg_threads,
        ) as motion_writer,
    ):
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index >= len(track):
                cap.release()
                raise RuntimeError(
                    f"Decoded more frames than detection cache for {source}"
                )
            foreground = bg.apply(frame, learningRate=args.bg_lr)
            foreground = cv2.morphologyEx(
                foreground, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)
            )
            record = track[frame_index]
            if not record["valid"]:
                display_box = record.get("display_box")
                if display_box is not None:
                    fallback = crop_square(
                        frame, display_box, args.size, args.pad
                    )
                    display_box_frames += 1
                else:
                    fallback = letterbox_square(frame, args.size)
                    letterbox_frames += 1
                gdino_writer.write(fallback)
                motion_writer.write(fallback)
                invalid_frames += 1
                previous_hit = False
                frame_index += 1
                continue

            base_box = record["camera_box"]
            gdino_crop = crop_square(frame, base_box, args.size, args.pad)
            camera_box = base_box
            is_anchor = frame_index in anchors
            if not is_anchor and frame_index >= args.bg_warmup_frames:
                camera_box, corrected, previous_hit = motion_correct_box(
                    foreground,
                    base_box,
                    previous_hit,
                    min_coverage=args.min_motion_coverage,
                    max_expansion_ratio=args.max_motion_expansion,
                )
                corrected_frames += int(corrected)
            else:
                previous_hit = False
            motion_crop = crop_square(frame, camera_box, args.size, args.pad)
            gdino_writer.write(gdino_crop)
            motion_writer.write(motion_crop)
            frame_index += 1
            if frame_index % 500 == 0:
                print(f"[render] {Path(video).name}: {frame_index} frames", flush=True)
    cap.release()
    if frame_index != len(track):
        raise RuntimeError(
            f"Decoded {frame_index} frames during render, expected {len(track)}: {source}"
        )
    os.replace(temporary_gdino, paths["gdino"])
    os.replace(temporary_motion, paths["gdino_motion"])

    metadata = {
        "schema": "cat-crop-render-v1",
        "status": "complete",
        "created_utc": utc_now(),
        "video": video,
        "source_path": str(source),
        "source_sha256": detection["source_sha256"],
        "fps": fps,
        "frames": frame_index,
        "size": args.size,
        "sample_stride": args.sample_stride,
        "max_gap": args.max_gap,
        "detection_fingerprint": detection["fingerprint"],
        "render_fingerprint": render_fingerprint(args),
        "valid_frames": frame_index - invalid_frames,
        "invalid_frames": invalid_frames,
        "display_box_fallback_frames": display_box_frames,
        "letterbox_fallback_frames": letterbox_frames,
        "corrected_frames": corrected_frames,
        "gdino_video": str(paths["gdino"]),
        "gdino_video_sha256": sha256(paths["gdino"]),
        "gdino_motion_video": str(paths["gdino_motion"]),
        "gdino_motion_video_sha256": sha256(paths["gdino_motion"]),
        "track": track,
    }
    atomic_json(paths["metadata"], metadata)
    print(
        f"[render] {Path(video).name}: frames={frame_index} "
        f"invalid={invalid_frames} corrected={corrected_frames}",
        flush=True,
    )
    return metadata


def render_fingerprint(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "size": args.size,
        "pad": args.pad,
        "sample_stride": args.sample_stride,
        "max_gap": args.max_gap,
        "bg_lr": args.bg_lr,
        "bg_warmup_frames": args.bg_warmup_frames,
        "min_motion_coverage": args.min_motion_coverage,
        "max_motion_expansion": args.max_motion_expansion,
        "crf": args.crf,
        "ffmpeg_threads": args.ffmpeg_threads,
        "invalid_frame_fallback": "cat-box-or-letterbox-v1",
        "target_policy": "single-pet-cat-or-dog-v1",
    }


def interval_availability(
    rows: list[dict[str, Any]], asset_root: Path
) -> list[dict[str, Any]]:
    tracks: dict[str, list[dict[str, Any]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for row in rows:
        video = row["video"]
        if video not in metadata:
            path = cache_paths(asset_root, video)["metadata"]
            metadata[video] = (
                json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            )
            if metadata[video]:
                tracks[video] = metadata[video]["track"]
        status = (
            interval_status(
                int(row["start_frame"]), int(row["end_frame"]), tracks[video]
            )
            if video in tracks
            else {
                "eligible": False,
                "reason": "crop_not_prepared",
                "invalid_frames": int(row["end_frame"]) - int(row["start_frame"]) + 1,
            }
        )
        interval_rows = (
            tracks[video][int(row["start_frame"]) - 1 : int(row["end_frame"])]
            if video in tracks
            else []
        )
        target_classes = {
            record.get("target_class")
            for record in interval_rows
            if record.get("valid") and record.get("target_class") is not None
        }
        results.append(
            {
                **row,
                "target_class": next(iter(target_classes)) if target_classes else None,
                "available": bool(status["eligible"]),
                "unavailable_reason": status["reason"],
                "invalid_frames": status["invalid_frames"],
                "source_video_sha256": metadata[video].get("source_sha256"),
                "gdino_video_sha256": metadata[video].get("gdino_video_sha256"),
                "gdino_motion_video_sha256": metadata[video].get(
                    "gdino_motion_video_sha256"
                ),
            }
        )
    return results


def build_indexes(
    source_rows: list[dict[str, Any]],
    asset_root: Path,
    dataset_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    availability = interval_availability(source_rows, asset_root)
    if dataset_root.exists() and any(dataset_root.iterdir()) and not args.force:
        raise RuntimeError(
            "Dataset root already contains files; use a new dataset root "
            f"or pass --force deliberately: {dataset_root}"
        )
    dataset_root.mkdir(parents=True, exist_ok=True)
    arm_rows: dict[str, dict[str, list[dict[str, Any]]]] = {
        arm: {split: [] for split in ("train", "val", "test")} for arm in ARMS
    }
    for row in availability:
        if not row["available"]:
            continue
        common = {
            key: row[key]
            for key in (
                "task_id",
                "start_frame",
                "end_frame",
                "label",
                "sample_id",
                "target_class",
            )
        }
        arm_rows["raw"][row["split"]].append({"video": row["video"], **common})
        relative_crop = f"videos/gdino/{Path(row['video']).stem}.mp4"
        relative_motion = f"videos/gdino_motion/{Path(row['video']).stem}.mp4"
        arm_rows["gdino"][row["split"]].append({"video": relative_crop, **common})
        arm_rows["gdino_motion"][row["split"]].append(
            {"video": relative_motion, **common}
        )

    split_files: dict[str, dict[str, str]] = {}
    class_counts: dict[str, dict[str, dict[str, int]]] = {}
    for arm in ARMS:
        class_counts[arm] = {}
        split_files[arm] = {}
        for split in ("train", "val", "test"):
            ordered = sorted(arm_rows[arm][split], key=lambda row: row["sample_id"])
            path = dataset_root / f"{arm}_{split}.jsonl"
            atomic_jsonl(path, ordered)
            split_files[arm][split] = str(path)
            class_counts[arm][split] = dict(
                Counter(CLASSES[row["label"]] for row in ordered)
            )

    availability_counts: dict[str, dict[str, Any]] = {}
    for split in ("train", "val", "test"):
        rows = [row for row in availability if row["split"] == split]
        availability_counts[split] = {
            "source_intervals": len(rows),
            "eligible_intervals": sum(row["available"] for row in rows),
            "unavailable_reasons": dict(
                Counter(
                    row["unavailable_reason"] for row in rows if not row["available"]
                )
            ),
            "eligible_classes": dict(
                Counter(CLASSES[row["label"]] for row in rows if row["available"])
            ),
            "eligible_target_classes": dict(
                Counter(
                    row.get("target_class", "cat")
                    for row in rows
                    if row["available"]
                )
            ),
        }
    manifest = {
        "schema": "cat-crop-dataset-v1",
        "created_utc": utc_now(),
        "dataset_id": args.dataset_id,
        "classes": CLASSES,
        "arms": list(ARMS),
        "common_sample_set": True,
        "source_index_root": str(args.index_root),
        "source_video_root": str(args.video_root),
        "asset_root": str(asset_root),
        "dataset_root": str(dataset_root),
        "source_rows": len(source_rows),
        "eligible_rows": sum(row["available"] for row in availability),
        "training_ready": args.max_videos is None and not args.video,
        "availability": availability_counts,
        "class_counts": class_counts,
        "split_files": split_files,
    }
    atomic_json(dataset_root / "manifest.json", manifest)
    availability_payload = {
        "schema": "cat-crop-availability-v1",
        "rows": [
            {
                key: row.get(key)
                for key in (
                    "sample_id",
                    "video",
                    "split",
                    "task_id",
                    "start_frame",
                    "end_frame",
                    "label",
                    "target_class",
                    "available",
                    "unavailable_reason",
                    "invalid_frames",
                    "source_video_sha256",
                )
            }
            for row in availability
        ],
    }
    atomic_json(dataset_root / "availability.json", availability_payload)
    if args.max_videos is None and not args.video:
        atomic_json(DEFAULT_RUN_ROOT / "availability.json", availability_payload)
    return manifest


def validate_args(args: argparse.Namespace) -> None:
    if args.index_root is None:
        raise ValueError("--index-root or CAT_ACTION_INDEX_ROOT is required")
    if args.video_root is None:
        raise ValueError("--video-root or CAT_ACTION_VIDEO_ROOT is required")
    if args.sample_stride < 1:
        raise ValueError("--sample-stride must be positive")
    if args.max_gap < args.sample_stride:
        raise ValueError("--max-gap must be at least the sample stride")
    if args.size < 1 or args.size % 2:
        raise ValueError("--size must be a positive even integer")
    if args.pad < 1:
        raise ValueError("--pad must be at least 1")
    if args.bg_warmup_frames < 0:
        raise ValueError("--bg-warmup-frames must be non-negative")
    if (
        args.torch_threads < 1
        or args.opencv_threads < 1
        or args.ffmpeg_threads < 1
    ):
        raise ValueError("thread limits must be positive")
    if args.crf < 0 or args.crf > 51:
        raise ValueError("--crf must be between 0 and 51")


def configure_opencv_threads(args: argparse.Namespace) -> None:
    cv2.setNumThreads(args.opencv_threads)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--index-root",
        type=Path,
        default=Path(os.environ.get("CAT_ACTION_INDEX_ROOT"))
        if os.environ.get("CAT_ACTION_INDEX_ROOT")
        else None,
    )
    parser.add_argument(
        "--video-root",
        type=Path,
        default=Path(os.environ.get("CAT_ACTION_VIDEO_ROOT"))
        if os.environ.get("CAT_ACTION_VIDEO_ROOT")
        else None,
    )
    parser.add_argument(
        "--asset-root",
        type=Path,
        default=DEFAULT_RUN_ROOT / "assets" / DEFAULT_DATASET_ID,
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=ROOT / "datasets/cat_crop_classification" / DEFAULT_DATASET_ID,
    )
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--video", action="append", default=[])
    parser.add_argument("--max-videos", type=int)
    parser.add_argument("--sample-stride", type=int, default=10)
    parser.add_argument("--max-gap", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--text-threshold", type=float, default=0.3)
    parser.add_argument("--model-dir", default="~/models/grounding-dino-tiny")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--torch-threads", type=int, default=2)
    parser.add_argument("--opencv-threads", type=int, default=2)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--pad", type=float, default=1.2)
    parser.add_argument("--bg-lr", type=float, default=0.002)
    parser.add_argument("--bg-warmup-frames", type=int, default=15)
    parser.add_argument("--min-motion-coverage", type=float, default=0.2)
    parser.add_argument("--max-motion-expansion", type=float, default=0.25)
    parser.add_argument("--crf", type=int, default=23)
    parser.add_argument("--ffmpeg-threads", type=int, default=1)
    parser.add_argument("--force", action="store_true")


def run_detect(args: argparse.Namespace, videos: list[str]) -> None:
    model_dir = Path(args.model_dir).expanduser()
    fingerprint = {
        **model_fingerprint(model_dir),
        "classes": ["cat", "dog"],
        "sample_stride": args.sample_stride,
        "box_threshold": args.threshold,
        "text_threshold": args.text_threshold,
    }
    detector = build_detector(args)
    for index, video in enumerate(videos, 1):
        print(f"[detect] {index}/{len(videos)} {video}", flush=True)
        detect_video(
            video,
            args.video_root,
            args.asset_root,
            detector,
            fingerprint,
            args,
        )


def run_render(args: argparse.Namespace, videos: list[str]) -> None:
    for index, video in enumerate(videos, 1):
        print(f"[render] {index}/{len(videos)} {video}", flush=True)
        render_video(video, args.video_root, args.asset_root, args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("detect", "render", "index", "all"),
        default="all",
    )
    add_common_arguments(parser)
    args = parser.parse_args()
    validate_args(args)
    configure_opencv_threads(args)
    rows, splits_by_video = source_records(args.index_root)
    videos = selected_videos(splits_by_video, args.video, args.max_videos)
    if args.stage in ("detect", "all"):
        run_detect(args, videos)
    if args.stage in ("render", "all"):
        run_render(args, videos)
    if args.stage in ("index", "all"):
        manifest = build_indexes(rows, args.asset_root, args.dataset_root, args)
        print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
