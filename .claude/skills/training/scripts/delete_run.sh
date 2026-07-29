#!/usr/bin/env bash
# delete_run.sh — 删除一个训练 run（work_dir + logs + checkpoints + metrics 记录）
#
# 用法：bash .claude/skills/training/scripts/delete_run.sh <run_id> [run_id2 ...]
# 示例：bash .claude/skills/training/scripts/delete_run.sh train-petmammal-v0-r2
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
PYTHON="~/miniconda3/envs/pet/bin/python"
REPO="~/pet-action-recognition"

if [ $# -eq 0 ]; then
  echo "用法: bash $0 <run_id> [run_id2 ...]"
  echo "先列出现有 runs: bash $0 --list"
  exit 1
fi

if [ "$1" = "--list" ]; then
  echo "=== 现有 runs ==="
  ssh -o ConnectTimeout=10 "$SSH_ALIAS" "$PYTHON -c \"
import json
d = json.load(open('$REPO/results/training/metrics.json'))
for r in d.get('runs', []):
    print(r['id'], r['status'])
\""
  exit 0
fi

for RUN_ID in "$@"; do
  echo "=== 删除 $RUN_ID ==="
  ssh -o ConnectTimeout=10 "$SSH_ALIAS" bash -c "'
    cd $REPO
    # work_dir
    rm -rf results/training/work_dirs/$RUN_ID/
    # log
    rm -f results/training/logs/${RUN_ID}.log
    # checkpoints (latest + best + pretrained 不删)
    find results/training/checkpoints/ -name \"${RUN_ID}_*.pth\" -delete 2>/dev/null
    find results/training/checkpoints/ -name \"${RUN_ID}_*.json\" -delete 2>/dev/null
    # metrics.json entry
    $PYTHON -c \"
import json, os
p = \\\"results/training/metrics.json\\\"
d = json.load(open(p))
d[\\\"runs\\\"] = [r for r in d.get(\\\"runs\\\",[]) if r.get(\\\"id\\\") != \\\"$RUN_ID\\\"]
tmp = p + \\\".tmp\\\"
with open(tmp, \\\"w\\\") as f: json.dump(d, f, ensure_ascii=False, indent=2)
os.replace(tmp, p)
print(\\\"  cleaned $RUN_ID\\\")\"'
  '
  echo "✅ $RUN_ID 已删除"
done
