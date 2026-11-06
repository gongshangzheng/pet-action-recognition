#!/bin/bash
# Train VideoMAEv2-B on the rendered 60-frame clip windows (ten classes).
set -euo pipefail

cd /home/wyy/pet-action-recognition

PYTHON="/home/wyy/miniconda3/envs/plf/bin/python"
CONFIG="configs/cat_clipv9_videomaev2_b.py"
WORK_DIR="results/cat_clip_v9/videomaev2_b/train20"

mkdir -p .run/guard .run/logs
export CUDA_VISIBLE_DEVICES=1
export OMP_NUM_THREADS=4
export PYTHONPATH=/home/wyy/pet-action-recognition

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Training on rendered clips..."

bash scripts/remote/resource_guard.sh run \
  --gpu-index 1 --max-gpu-mem-pct 92 --max-cpu-pct 900 --max-rss-mb 24000 \
  --timeout-s 20000 --log .run/guard/clipv9_train_20261107.log \
  -- "${PYTHON}" models/mmaction2/tools/train.py "${CONFIG}" --cfg-options work_dir="${WORK_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Clip training finished."
