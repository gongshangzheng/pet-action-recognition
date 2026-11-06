#!/bin/bash
# Train the ten-class VideoMAEv2-B model on the clip dataset (20 epochs).
set -euo pipefail

cd /home/wyy/pet-action-recognition

PYTHON="/home/wyy/miniconda3/envs/plf/bin/python"
CONFIG="configs/cat_clip_videomaev2_b.py"
WORK_DIR="results/cat_clip_v8/train20"

mkdir -p .run/guard .run/logs
export CUDA_VISIBLE_DEVICES=1
export OMP_NUM_THREADS=4
export PYTHONPATH=/home/wyy/pet-action-recognition

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting 20-epoch clip training..."

bash scripts/remote/resource_guard.sh run \
  --gpu-index 1 \
  --max-gpu-mem-pct 92 \
  --max-cpu-pct 900 \
  --max-rss-mb 24000 \
  --timeout-s 20000 \
  --log .run/guard/clip_train_20261107.log \
  -- "${PYTHON}" models/mmaction2/tools/train.py "${CONFIG}" \
    --cfg-options work_dir="${WORK_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Clip training finished."
