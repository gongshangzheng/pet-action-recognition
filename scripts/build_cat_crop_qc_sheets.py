#!/usr/bin/env python3
"""Build randomized raw/grounding-dino/motion quality-control contact sheets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPTS = ROOT / "scripts/checks"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CHECK_SCRIPTS))

from check_cat_crop_experiment import validate_metadata  # noqa: E402

VARIANTS = ("raw", "gdino", "gdino_motion")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def review_order(sample_id: str, salt: str) -> list[str]:
    return sorted(
        VARIANTS,
        key=lambda variant: hashlib.sha256(
            f"{salt}:{sample_id}:{variant}".encode()
        ).hexdigest(),
    )


def letterbox(frame: np.ndarray, size: int) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = min(size / width, size / height)
    resized = cv2.resize(
        frame,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((size, size, 3), 32, dtype=np.uint8)
    top = (size - resized.shape[0]) // 2
    left = (size - resized.shape[1]) // 2
    canvas[top : top + resized.shape[0], left : left + resized.shape[1]] = resized
    return canvas


def read_frame(path: Path, frame_index: int, size: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot decode frame {frame_index}: {path}")
    return letterbox(frame, size)


def add_header(image: np.ndarray, text: str) -> np.ndarray:
    header = 34
    canvas = np.full((image.shape[0] + header, image.shape[1], 3), 18, np.uint8)
    canvas[header:] = image
    cv2.putText(
        canvas,
        text,
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (235, 235, 235),
        1,
        cv2.LINE_AA,
    )
    return canvas


def write_source_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "review_id",
        "sample_id",
        "video",
        "class_name",
        "start_frame",
        "end_frame",
        "event_hour",
        "selection_reasons",
        "source_sha256",
        "gdino_sha256",
        "gdino_motion_sha256",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{field: row.get(field) for field in fields},
                    "selection_reasons": "|".join(row["selection_reasons"]),
                }
            )


def write_review_form(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "review_id",
        "body_cut_ok",
        "target_jump_ok",
        "jitter_ok",
        "text_clean_ok",
        "notes",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"review_id": row["review_id"]})


def prepare_review_rows(
    rows: list[dict[str, Any]],
    video_root: Path,
    asset_root: Path,
) -> list[dict[str, Any]]:
    prepared = []
    for position, row in enumerate(rows, 1):
        metadata = validate_metadata(str(row["video"]), asset_root)
        raw_path = video_root / row["video"]
        if sha256(raw_path) != metadata["source_sha256"]:
            raise ValueError(f"raw video hash mismatch: {raw_path}")
        stem = Path(row["video"]).stem
        paths = {
            "raw": raw_path,
            "gdino": Path(metadata["gdino_video"]),
            "gdino_motion": Path(metadata["gdino_motion_video"]),
        }
        for variant, path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(f"{variant} video missing: {path}")
        prepared.append(
            {
                **row,
                "review_id": f"Q{position:03d}",
                "_paths": paths,
                "_metadata": metadata,
            }
        )
    return prepared


def render_sheet(
    row: dict[str, Any],
    sheets_root: Path,
    size: int,
    salt: str,
) -> dict[str, Any]:
    review_id = row["review_id"]
    order = review_order(row["sample_id"], salt)
    frame_numbers = (
        int(row["start_frame"]),
        (int(row["start_frame"]) + int(row["end_frame"])) // 2,
        int(row["end_frame"]),
    )
    grid_rows = []
    for frame_number in frame_numbers:
        panels = [
            read_frame(row["_paths"][variant], frame_number - 1, size)
            for variant in order
        ]
        grid_rows.append(
            add_header(
                np.hstack(panels),
                f"{review_id} | source frame {frame_number}",
            )
        )
    sheet_path = sheets_root / f"{review_id}.jpg"
    if not cv2.imwrite(
        str(sheet_path),
        np.vstack(grid_rows),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    ):
        raise RuntimeError(f"cannot write contact sheet: {sheet_path}")
    metadata = row["_metadata"]
    return {
        **{key: value for key, value in row.items() if not key.startswith("_")},
        "sheet": str(sheet_path),
        "sheet_sha256": sha256(sheet_path),
        "hidden_column_order": order,
        "source_path": str(row["_paths"]["raw"]),
        "source_sha256": metadata["source_sha256"],
        "gdino_path": str(row["_paths"]["gdino"]),
        "gdino_sha256": metadata["gdino_video_sha256"],
        "gdino_motion_path": str(row["_paths"]["gdino_motion"]),
        "gdino_motion_sha256": metadata["gdino_motion_video_sha256"],
    }


def write_outputs(
    out_root: Path,
    selection_path: Path,
    review_rows: list[dict[str, Any]],
) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    write_source_table(out_root / "source.csv", review_rows)
    write_review_form(out_root / "review_form.csv", review_rows)
    manifest = {
        "schema": "cat-crop-qc-sheets-v1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selection": str(selection_path),
        "selection_sha256": sha256(selection_path),
        "sheet_count": len(review_rows),
        "hidden_column_order": "Each sheet uses deterministic per-sample order.",
        "rows": review_rows,
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_root / "README.md").write_text(
        "# Cat crop quality review\n\n"
        "Inspect `sheets/Q*.jpg` before opening `manifest.json`. Each row shows "
        "three source frames and each column is one hidden variant. Record cut-off "
        "body, target jumping, jitter and overlaid text for every sheet.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--opencv-threads", type=int, default=2)
    parser.add_argument("--salt", default="gdino-crop-20261103a-quality-review-v1")
    args = parser.parse_args()
    if not 64 <= args.size <= 1024:
        raise ValueError("--size must be between 64 and 1024")
    if args.opencv_threads < 1:
        raise ValueError("--opencv-threads must be positive")
    cv2.setNumThreads(args.opencv_threads)

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    prepared = prepare_review_rows(
        selection["rows"],
        args.video_root,
        args.asset_root,
    )
    sheets_root = args.out_root / "sheets"
    sheets_root.mkdir(parents=True, exist_ok=True)
    review_rows = []
    for position, row in enumerate(prepared, 1):
        review_rows.append(render_sheet(row, sheets_root, args.size, args.salt))
        print(f"[qc] {position}/{len(prepared)} {row['review_id']}", flush=True)
    write_outputs(args.out_root, args.selection, review_rows)
    print(
        json.dumps(
            {"sheet_count": len(review_rows), "out_root": str(args.out_root)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
