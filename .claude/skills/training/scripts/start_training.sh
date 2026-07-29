#!/usr/bin/env bash
# start_training.sh — 在 pet 上启动一个训练 run
#
# 用法：
#   bash .claude/skills/training/scripts/start_training.sh \
#     --model-id tsn-resnet50-quadruped \
#     --dataset-id pet_action_mammal_v0 \
#     --pretrained checkpoints/tsn-resnet50/tsn-resnet50_pretrained.pth \
#     --epochs 50 --batch-size 8 --device cuda --num-classes 8 \
#     --vis-interval 10
#
# 所有参数直接传给 scripts/train_model.py，另加：
#   --run-id   自动生成（或手动指定）
#   --cwd      自动设为 pet 上的 repo 根
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
PYTHON="~/miniconda3/envs/pet/bin/python"
REPO="~/pet-action-recognition"

# 解析 --run-id（如果没给，自动生成）
RUN_ID=""
PASS_THROUGH=()
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2 ;;
    *) PASS_THROUGH+=("$1"); shift ;;
  esac
done

if [ -z "$RUN_ID" ]; then
  RUN_ID="train-$(date +%Y%m%d-%H%M%S)"
  echo "[info] 自动生成 run_id: $RUN_ID"
fi

echo "=== 启动训练: $RUN_ID ==="
echo "[cmd] train_model.py ${PASS_THROUGH[*]} --run-id $RUN_ID"

ssh -o ConnectTimeout=10 "$SSH_ALIAS" \
  "cd $REPO && nohup $PYTHON scripts/train_model.py \
    --run-id $RUN_ID \
    ${PASS_THROUGH[*]} \
    > /tmp/train-${RUN_ID}.log 2>&1 < /dev/null & \
   echo started"

echo "=== 训练已启动（后台）==="
echo "  run_id: $RUN_ID"
echo "  日志:   ssh $SSH_ALIAS 'tail -f /tmp/train-${RUN_ID}.log'"
echo "  查进度: curl http://localhost:8788/api/training/runs/$RUN_ID"
echo "  详情页: http://localhost:3000/pet-action-recognition/training/runs/$RUN_ID"
