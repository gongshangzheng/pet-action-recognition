#!/bin/bash
# Render every clip window to a 256x256 mp4 using the per-frame boxes.
set -euo pipefail

cd /home/wyy/pet-action-recognition

PYTHON="/home/wyy/miniconda3/envs/plf/bin/python"
CLIPS="results/cat_clip_v9/index/clips_v9.jsonl"
VIDEO_ROOT="/home/wyy/pet-final/datasets/cat_raw"
OUT="results/cat_clip_v9/assets/clips"

mkdir -p .run/guard .run/logs
export OPENCV_FFMPEG_THREADS=1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rendering clip windows..."

bash scripts/remote/resource_guard.sh run \
  --gpu-index 1 \
  --max-gpu-mem-pct 92 \
  --max-cpu-pct 900 \
  --max-rss-mb 16000 \
  --timeout-s 7200 \
  --log .run/guard/clip_render_20261107.log \
  -- "${PYTHON}" scripts/render_clip_windows.py \
    --clips "${CLIPS}" --video-root "${VIDEO_ROOT}" --out "${OUT}" --workers 8

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Clip rendering finished."
