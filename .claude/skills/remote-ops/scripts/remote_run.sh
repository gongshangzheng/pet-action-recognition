#!/bin/bash
# Run a command on the remote machine under the resource guard.
#
# The guard is piped over ssh rather than read from the remote checkout, so this
# works even when the deployed tree is stale — which is exactly when a guarded
# run matters most. Defaults are deliberately conservative: bounded threads, low
# priority, and a watchdog that kills the process tree on CPU/RSS/GPU/time breach.
#
# Usage:
#   bash remote_run.sh -- python3 bench.py --flag
#   bash remote_run.sh --max-cpu-pct 200 --timeout-s 600 -- python3 bench.py
#   bash remote_run.sh --gpu-index 1 --max-gpu-mem-pct 80 -- train.py
#
# Exit codes: 0 ok / 1 usage or unreachable / 4 killed by the guard / 5 command failed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_remote_common.sh"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || $# -eq 0 ]]; then
  sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
fi

SKIP_PREFLIGHT=0
GPU_INDEX_FOR_PREFLIGHT=""
GLUE=()
while [[ $# -gt 0 && "$1" != "--" ]]; do
  case "$1" in
    --skip-preflight) SKIP_PREFLIGHT=1; shift ;;
    --gpu-index) GPU_INDEX_FOR_PREFLIGHT="$2"; GLUE+=("$1" "$2"); shift 2 ;;
    *) GLUE+=("$1"); shift ;;
  esac
done
[[ "${1:-}" == "--" ]] && shift
if [[ $# -eq 0 ]]; then
  die "no command given (usage: remote_run.sh [guard options] -- <command...>)"
fi

# 默认先跑容量预检：预检不通过就**不跑**（退出码沿用 1/2/3），
# 避免「明明 GPU 有人占着还照跑」——真实事故：2026-10-29 我在 preflight 返回 2 之后仍然启动了训练。
if (( SKIP_PREFLIGHT == 0 )); then
  echo "### 自动预检（可用 --skip-preflight 关闭）"
  PREFLIGHT_ARGS=()
  [[ -n "$GPU_INDEX_FOR_PREFLIGHT" ]] && PREFLIGHT_ARGS+=(--gpu-index "$GPU_INDEX_FOR_PREFLIGHT")
  if ! bash "$SCRIPT_DIR/preflight.sh" "${PREFLIGHT_ARGS[@]}"; then
    rc=$?
    echo "预检未通过（退出码 $rc）→ 不执行命令。等机器空下来或与占用者协调后再跑。" >&2
    exit "$rc"
  fi
fi

# Quote the remote command so the guard receives it as one argument string.
REMOTE_CMD=$(printf '%q ' "$@")
ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "cd '$REMOTE_ROOT' && bash -s -- run ${GLUE[*]} -- $REMOTE_CMD" < "$SCRIPT_DIR/resource_guard.sh"
rc=$?
case $rc in
  0) exit 0 ;;
  4) echo "guard 因超出 CPU/RSS/GPU/时长上限终止了该命令" >&2; exit 4 ;;
  255) echo "无法连接 $REMOTE" >&2; exit 1 ;;
  *) exit 5 ;;
esac
