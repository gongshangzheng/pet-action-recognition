#!/bin/bash
# Detect the annotated videos that the previous run never touched.
#
# Detection previously ran only on videos referenced by the post-overlap index,
# so the 429 videos whose intervals were filtered out have no detection cache and
# cannot be classified as single- or multi-cat.
set -euo pipefail

cd /home/wyy/pet-action-recognition

INDEX_ROOT="/home/wyy/pet-final/datasets/cat_action_v1"
VIDEO_ROOT="/home/wyy/pet-final/datasets/cat_raw"
ASSET_ROOT="results/cat_crop_classification/gdino-crop-20261103a/assets/full_run"
DATASET_ROOT="datasets/cat_crop_classification/gdino-v1-full"
VIDEO_LIST="tmp/detect_missing_videos.txt"
PYTHON="/home/wyy/miniconda3/envs/plf/bin/python"

mkdir -p .run/guard .run/logs
export CUDA_VISIBLE_DEVICES=1
export OPENCV_FFMPEG_THREADS=1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting missing-video detection ($(wc -l < "${VIDEO_LIST}") videos)..."

bash scripts/remote/resource_guard.sh run \
  --gpu-index 1 \
  --max-gpu-mem-pct 90 \
  --max-cpu-pct 350 \
  --max-rss-mb 10000 \
  --timeout-s 7200 \
  --log .run/guard/detect_missing_20261107.log \
  -- "${PYTHON}" scripts/prepare_cat_crop_experiment.py \
    --stage detect \
    --index-root "${INDEX_ROOT}" \
    --video-root "${VIDEO_ROOT}" \
    --asset-root "${ASSET_ROOT}" \
    --dataset-root "${DATASET_ROOT}" \
    --video-list "${VIDEO_LIST}" \
    --sample-stride 5 \
    --max-gap 10 \
    --device cuda:0 \
    --torch-threads 1 \
    --opencv-threads 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Missing-video detection finished."
