#!/usr/bin/env bash
# resume_training.sh — 断点续训一个已有的 run
#
# 用法：
#   bash .claude/skills/training/scripts/resume_training.sh <run_id> [额外参数...]
#
# 会自动找到该 run 的 latest checkpoint，用 -r/--resume 继续。
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
PYTHON="~/miniconda3/envs/pet/bin/python"
REPO="~/pet-action-recognition"

if [ $# -lt 1 ]; then
  echo "用法: bash $0 <run_id> [额外参数...]"
  echo "先列出现有 runs: bash .claude/skills/training/scripts/delete_run.sh --list"
  exit 1
fi

RUN_ID="$1"
shift

echo "=== 续训: $RUN_ID ==="

# 在 pet 上找 latest checkpoint + 原 model/dataset/config
ssh -o ConnectTimeout=10 "$SSH_ALIAS" "$PYTHON -c \"
import json, os, glob
d = json.load(open('$REPO/results/training/metrics.json'))
r = next((x for x in d.get('runs',[]) if x['id'] == '$RUN_ID'), None)
if not r:
    print('ERROR: run $RUN_ID not found')
    exit(1)
# 找 latest checkpoint
ckpts = sorted(glob.glob('$REPO/results/training/work_dirs/$RUN_ID/epoch_*.pth'))
if not ckpts:
    print('ERROR: no epoch checkpoint in work_dir')
    exit(1)
latest = ckpts[-1]
print(f'latest={latest}')
print(f'model={r[\"model\"]}')
print(f'dataset={r[\"dataset\"]}')
print(f'epochs={r.get(\"epochs\", 100)}')
\""

if [ $? -ne 0 ]; then
  echo "❌ 找不到 run 或 checkpoint"
  exit 1
fi

echo "=== 启动续训（后台）==="
ssh -o ConnectTimeout=10 "$SSH_ALIAS" \
  "cd $REPO && nohup $PYTHON scripts/train_model.py \
    --run-id $RUN_ID \
    --resume auto \
    $(printf '%q ' \"\$@\") \
    > /tmp/train-${RUN_ID}-resume.log 2>&1 < /dev/null & \
   echo 'started pid '$!"

echo "  run_id: $RUN_ID"
echo "  日志:   ssh $SSH_ALIAS 'tail -f /tmp/train-${RUN_ID}-resume.log'"
