"""Create an immutable version of a source video path inventory."""

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}


def validate_records(records):
    """Reject duplicate identities before writing any inventory."""
    seen = set()
    for record in records:
        video_id = record['video_id']
        if video_id in seen:
            raise ValueError(f'duplicate video_id: {video_id}')
        seen.add(video_id)


def build_video_manifest(video_root, output_dir):
    """Discover paths without opening media and publish to a new directory."""
    root = Path(video_root).resolve()
    output = Path(output_dir)
    if not root.is_dir():
        raise NotADirectoryError(f'video root is not a directory: {root}')

    def raise_walk_error(error):
        raise error

    paths = []
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=raise_walk_error):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if path.suffix.lower() in VIDEO_EXTS and stat.S_ISREG(path.lstat().st_mode):
                paths.append(path.relative_to(root).as_posix())
    records = [{'video_id': path, 'path': path} for path in sorted(paths)]
    if not records:
        raise ValueError(f'no video files found in {root}')
    validate_records(records)
    data = ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records).encode('utf-8')
    metadata = {'format_version': 1, 'video_root': str(root), 'count': len(records),
                'videos_sha256': hashlib.sha256(data).hexdigest()}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'videos.jsonl').write_bytes(data)
    (output / 'manifest.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video-root', type=Path, required=True, help='source video directory to scan recursively')
    parser.add_argument('--output-dir', type=Path, required=True, help='new inventory version directory')
    args = parser.parse_args()
    metadata = build_video_manifest(args.video_root, args.output_dir)
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    main()
