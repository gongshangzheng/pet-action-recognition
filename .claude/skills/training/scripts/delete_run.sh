#!/usr/bin/env bash
# delete_run.sh — 删除一个训练进程的所有产物（work_dir + logs + checkpoints + metrics + vis_samples）
#
# 用法：bash .claude/skills/training/scripts/delete_run.sh <run_id> [run_id2 ...]
#       bash .claude/skills/training/scripts/delete_run.sh --list
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
PYTHON="~/miniconda3/envs/pet/bin/python"
REPO="~/pet-action-recognition"

if [ $# -eq 0 ]; then
  echo "用法: bash $0 <run_id> [run_id2 ...]"
  echo "列出现有进程: bash $0 --list"
  exit 1
fi

if [ "$1" = "--list" ]; then
  ssh -o ConnectTimeout=10 "$SSH_ALIAS" "$PYTHON -c \"
import json
d = json.load(open('$REPO/results/training/metrics.json'))
if not d.get('runs'):
    print('(no runs)')
for r in d.get('runs', []):
    print(r['id'], r.get('name',''), r['status'])
\""
  exit 0
fi

for RUN_ID in "$@"; do
  echo "=== 删除 $RUN_ID ==="
  ssh -o ConnectTimeout=10 "$SSH_ALIAS" "$PYTHON -c \"
import json, os, glob, shutil
run_id = '$RUN_ID'
repo = os.path.expanduser('$REPO')

# 1. work_dir（含 vis_samples、checkpoints、scalars）
wd = os.path.join(repo, 'results/training/work_dirs/' + run_id)
if os.path.isdir(wd):
    shutil.rmtree(wd)
    print('  [1] work_dir: deleted')
else:
    print('  [1] work_dir: not found')

# 2. training log
log = os.path.join(repo, 'results/training/logs/' + run_id + '.log')
if os.path.isfile(log):
    os.remove(log)
    print('  [2] log: deleted')
else:
    print('  [2] log: not found')

# 3. checkpoints（trained latest + best；pretrained 不删）
cp_dir = os.path.join(repo, 'checkpoints')
removed_ckpts = 0
for root, dirs, files in os.walk(cp_dir):
    for fn in files:
        if fn.startswith(run_id + '_') and (fn.endswith('.pth') or fn.endswith('.json')):
            os.remove(os.path.join(root, fn))
            removed_ckpts += 1
# 删空目录
for root, dirs, files in os.walk(cp_dir, topdown=False):
    for d in dirs:
        full = os.path.join(root, d)
        if os.path.isdir(full) and not os.listdir(full):
            os.rmdir(full)
print('  [3] checkpoints: ' + str(removed_ckpts) + ' files deleted')

# 4. metrics.json entry
mp = os.path.join(repo, 'results/training/metrics.json')
if os.path.isfile(mp):
    d = json.load(open(mp))
    before = len(d.get('runs', []))
    d['runs'] = [r for r in d.get('runs', []) if r.get('id') != run_id]
    after = len(d['runs'])
    tmp = mp + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, mp)
    print('  [4] metrics.json: ' + str(before - after) + ' entries removed')
else:
    print('  [4] metrics.json: not found')

print('  done')
\""
  echo "  $RUN_ID 已删除"
done
