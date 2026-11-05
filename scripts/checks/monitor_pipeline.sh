#!/bin/bash
set -u

cd /home/wyy/pet-action-recognition

LOG_FILE=".run/logs/full_preprocessing.log"
GUARD_LOG_DIR=".run/guard"
ALERT_FILE=".run/alert_status.json"
DATASET_DIR="datasets/cat_crop_classification/gdino-v1-full"
ASSET_DIR="results/cat_crop_classification/gdino-crop-20261103a/assets/full_run"
STAGE_TRACKER=".run/stage_status.json"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# 1. Check for errors in logs
error_found=0
alert_reason=""

# Check for python tracebacks in the main log
if grep -En "(Traceback|RuntimeError|Exception|Error:)" "$LOG_FILE" 2>/dev/null | tail -n 5 > /tmp/log_errors.txt; then
  if [[ -s /tmp/log_errors.txt ]]; then
    error_found=1
    alert_reason="Python error/exception detected in log: $(cat /tmp/log_errors.txt | head -n 1)"
  fi
fi

current_stage="UNKNOWN"
if grep -q "Full preprocessing finished successfully!" "$LOG_FILE" 2>/dev/null; then
  current_stage="COMPLETED"
elif grep -q "Stage 3: Build manifest and indexes..." "$LOG_FILE" 2>/dev/null; then
  current_stage="STAGE_3_INDEX"
elif grep -q "Stage 2: Render B & C crops..." "$LOG_FILE" 2>/dev/null; then
  current_stage="STAGE_2_RENDER"
elif grep -q "Stage 1: Detection..." "$LOG_FILE" 2>/dev/null; then
  current_stage="STAGE_1_DETECT"
fi

# 2. Check running processes
pipeline_pid=$(pgrep -f 'run_full_preprocessing.sh' || true)
python_pid=$(pgrep -f 'prepare_cat_crop_experiment.py' || true)

# Count current assets
asset_count=$(find "$ASSET_DIR" -type f 2>/dev/null | wc -l)

# 3. Check completion
if grep -q "Full preprocessing finished successfully!" "$LOG_FILE" 2>/dev/null; then
  echo "[STATUS: COMPLETED] Full preprocessing pipeline finished successfully!"
  echo "Checking dataset integrity in $DATASET_DIR..."
  ls -lh "$DATASET_DIR"
  exit 0
fi

# 4. Check if stalled or died unexpectedly
if [[ -z "$pipeline_pid" && -z "$python_pid" ]]; then
  error_found=1
  alert_reason="CRITICAL: Preprocessing pipeline processes are NOT running and job is not marked complete!"
fi

# Output current monitoring state
echo "=== [$timestamp] Pipeline Monitor ==="
if (( error_found )); then
  echo "[ALERT: HOOK TRIGGERED] $alert_reason"
  cat << JSON > "$ALERT_FILE"
{
  "timestamp": "$timestamp",
  "status": "ALERT",
  "reason": "$alert_reason",
  "asset_count": $asset_count
}
JSON
  exit 1
else
  echo "[STATUS: HEALTHY] Processes running (pipeline PID: $pipeline_pid, python PID: $python_pid)"
echo "[STAGE] Current execution stage: $current_stage"
  echo "[PROGRESS] Total assets generated: $asset_count"
  echo "[LATEST LOGS]"
  tail -n 8 "$LOG_FILE"
  echo "[GPU STATUS]"
  nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader
  cat << JSON > "$ALERT_FILE"
{
  "timestamp": "$timestamp",
  "status": "HEALTHY",
  "pipeline_pid": "$pipeline_pid",
  "python_pid": "$python_pid",
  "asset_count": $asset_count
}
JSON
  exit 0
fi
