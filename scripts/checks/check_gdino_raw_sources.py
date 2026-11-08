#!/usr/bin/env python3
"""Check manifest sources' first frames; write an explicit unreadable-source ledger.

Run at low priority with one OpenCV/FFmpeg thread. Decoder diagnostics remain on
stderr for the operator to retain alongside the ledger. This is not a full decode.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    videos = args.manifest.read_text().splitlines()
    if not videos or len(videos) != len(set(videos)):
        raise ValueError("manifest must contain unique videos")
    cv2.setNumThreads(1)
    failures = []
    for index, video in enumerate(videos, 1):
        relative = Path(video)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"invalid video path: {video}")
        source = args.video_root / relative
        before = source.stat()
        capture = cv2.VideoCapture(str(source))
        opened = capture.isOpened()
        ok, _ = capture.read() if opened else (False, None)
        capture.release()
        if not opened or not ok:
            sha = digest(source)
            after = source.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise RuntimeError(f"source changed during inspection: {video}")
            failures.append({"video": video, "status": "source_unreadable", "size_bytes": after.st_size,
                             "source_sha256": sha, "error": "OpenCV VideoCapture could not open source" if not opened else "OpenCV could not read first frame"})
            print(f"FAILED {video}: {failures[-1]['error']}", flush=True)
        if index % 100 == 0 or index == len(videos):
            print(f"checked {index}/{len(videos)}; unreadable={len(failures)}", flush=True)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite ledger: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema": "gdino-source-failures-v1", "manifest_sha256": digest(args.manifest),
                                      "checked": len(videos), "failures": failures}, indent=2) + "\n")


if __name__ == "__main__":
    main()
