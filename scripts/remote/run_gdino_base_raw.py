#!/usr/bin/env python3
"""Prepare a pinned base snapshot and run one guarded, resumable detection batch.

Run each smoke/batch invocation detached by the operator; each invocation repeats
preflight. The single-video smoke is technical validation, not quality approval.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "IDEA-Research/grounding-dino-base"
REVISION = "12bdfa3120f3e7ec7b434d90674b3396eccf88eb"
WEIGHT_SHA = "5548f844c928c4b6f411fa8cbcc2bfa8dbbba437cb1d513975519f93c2a9ed21"
FILES = ["model.safetensors", "config.json", "preprocessor_config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt"]
GUARD = ".claude/skills/remote-ops/scripts/resource_guard.sh"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_source_failures(path, manifest, videos, video_root):
    """Validate explicit, fingerprinted unreadable sources before excluding them."""
    if path is None:
        return set()
    data = json.loads(path.read_text())
    if (data.get("schema") != "gdino-source-failures-v1" or data.get("manifest_sha256") != digest(manifest)
            or data.get("checked") != len(videos) or not isinstance(data.get("failures"), list)):
        raise ValueError("invalid source failure ledger")
    failures = set()
    for entry in data["failures"]:
        video = entry.get("video")
        if (video not in videos or video in failures or entry.get("status") != "source_unreadable"
                or not isinstance(entry.get("error"), str) or not entry["error"]):
            raise ValueError(f"invalid source failure entry: {video}")
        source = video_root / video
        if source.stat().st_size != entry.get("size_bytes") or digest(source) != entry.get("source_sha256"):
            raise ValueError(f"source failure fingerprint mismatch: {video}")
        failures.add(video)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download", "prepare", "smoke", "batch", "all"))
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True, help="dataset root containing videos/")
    parser.add_argument("--index-root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, default=Path("/home/wyy/models/grounding-dino-base"))
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--start", type=int, default=0, help="zero-based manifest offset")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--source-failures", type=Path, help="explicit fingerprinted unreadable-source ledger")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    asset = args.asset_root.resolve()
    model = args.model_dir.resolve()
    video_root = args.video_root.resolve()
    manifest = run / "videos.txt"
    if args.action == "download":
        from huggingface_hub import snapshot_download
        weight = model / "model.safetensors"
        if weight.exists() and (weight.stat().st_size != 933400872 or digest(weight) != WEIGHT_SHA):
            raise RuntimeError("Existing weights differ; refusing to overwrite")
        snapshot_download(repo_id=REPO, revision=REVISION, local_dir=str(model), allow_patterns=FILES, endpoint=args.endpoint)
        if any(not (model / name).is_file() for name in FILES) or weight.stat().st_size != 933400872 or digest(weight) != WEIGHT_SHA:
            raise RuntimeError("Model snapshot missing files or weight size/hash mismatch")
        return
    if args.action == "prepare":
        weight = model / "model.safetensors"
        if any(not (model / name).is_file() for name in FILES) or weight.stat().st_size != 933400872 or digest(weight) != WEIGHT_SHA:
            raise RuntimeError("Model snapshot missing files or weight size/hash mismatch")
        files = sorted(p for p in (video_root / "videos").iterdir() if p.is_file() and p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"})
        if len(files) != 2737 or len({p.name for p in files}) != len(files) or len({p.stem for p in files}) != len(files):
            raise RuntimeError(f"Expected 2737 videos with unique names and stems; got {len(files)}")
        if manifest.exists() or asset.exists():
            raise RuntimeError("Run manifest or asset root already exists; choose a new run")
        run.mkdir(parents=True, exist_ok=True)
        manifest.write_text("".join(f"videos/{p.name}\n" for p in files))
        (run / "manifest.json").write_text(json.dumps({"repository": REPO, "revision": REVISION, "weight_sha256": WEIGHT_SHA, "model_dir": str(model), "video_root": str(video_root), "index_root": str(args.index_root.resolve()), "asset_root": str(asset), "videos": len(files), "video_list_sha256": digest(manifest), "stride": 5, "box_threshold": 0.3, "text_threshold": 0.3, "raw_candidates_version": 1, "quality": "unaccepted"}, indent=2) + "\n")
        return
    meta = json.loads((run / "manifest.json").read_text())
    expected = {"repository": REPO, "revision": REVISION, "weight_sha256": WEIGHT_SHA,
                "asset_root": str(asset), "video_root": str(video_root), "model_dir": str(model),
                "index_root": str(args.index_root.resolve()), "video_list_sha256": digest(manifest),
                "stride": 5, "box_threshold": 0.3, "text_threshold": 0.3,
                "raw_candidates_version": 1, "quality": "unaccepted", "videos": 2737}
    if any(meta.get(key) != value for key, value in expected.items()) or digest(model / "model.safetensors") != WEIGHT_SHA:
        raise RuntimeError("Run metadata, paths, manifest or weights do not match preparation")
    videos = manifest.read_text().splitlines()
    if len(videos) != 2737 or args.start < 0 or args.count < 1 or args.start >= len(videos):
        raise ValueError("invalid manifest or batch range")
    if args.action == "smoke" and args.count != 1:
        raise ValueError("smoke requires count 1")
    if args.action != "all" and args.start + args.count > len(videos):
        raise ValueError("batch exceeds manifest")
    if args.source_failures and args.action != "all":
        raise ValueError("source failure ledger is only supported by all")
    failures = load_source_failures(args.source_failures, manifest, videos, video_root)
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", GUARD], cwd=ROOT, check=True)
    guard = ["bash", str(ROOT / GUARD)]
    starts = range(args.start, len(videos), args.count) if args.action == "all" else [args.start]
    env = {**os.environ, "OPENCV_FFMPEG_THREADS": "1"}
    attempt = str(time.time_ns()) if args.source_failures else None
    for start in starts:
        count = min(args.count, len(videos) - start)
        label = f"{args.action}-{start}-{count}" + (f".resume-{attempt}" if attempt else "")
        selected = run / f"{label}.txt"
        selected_videos = [video for video in videos[start:start + count] if video not in failures]
        selected.write_text("".join(f"{video}\n" for video in selected_videos))
        if not selected_videos:
            (run / f"{label}.status.json").write_text(json.dumps({"phase": "source_failures_only", "returncode": 0, "start": start, "count": count}) + "\n")
            continue
        preflight = subprocess.run(guard + ["preflight", "--gpu-index", str(args.gpu_index)], cwd=ROOT, env=env)
        if preflight.returncode:
            (run / f"{label}.status.json").write_text(json.dumps({"phase": "preflight", "returncode": preflight.returncode, "start": start, "count": count}) + "\n")
            sys.exit(preflight.returncode)
        cmd = [sys.executable, str(ROOT / "scripts/prepare_cat_crop_experiment.py"), "--stage", "detect", "--index-root", str(args.index_root.resolve()), "--video-root", str(video_root), "--asset-root", str(asset), "--video-list", str(selected), "--model-dir", str(model), "--device", f"cuda:{args.gpu_index}", "--sample-stride", "5", "--threshold", "0.3", "--text-threshold", "0.3", "--torch-threads", "1", "--opencv-threads", "1", "--require-raw-candidates"]
        status = subprocess.run(guard + ["run", "--gpu-index", str(args.gpu_index), "--max-cpu-pct", "250", "--max-rss-mb", "24000", "--max-gpu-mem-pct", "90", "--threads", "2", "--nice", "10", "--timeout-s", "10800", "--log", str(run / f"{label}.guard.log"), "--"] + cmd, cwd=ROOT, env=env)
        (run / f"{label}.status.json").write_text(json.dumps({"phase": "detect", "returncode": status.returncode, "start": start, "count": count}) + "\n")
        if status.returncode:
            sys.exit(status.returncode)



if __name__ == "__main__":
    main()
