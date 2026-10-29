#!/bin/bash
# 容量预检（在 pet 上执行，本地发起）。守卫脚本本身用管道送过去，远端仓库陈旧也能用。
#
# 用法：
#   bash preflight.sh                    # 所有 GPU + load/内存/磁盘
#   bash preflight.sh --gpu-index 0      # 只看 GPU0
#   bash preflight.sh --gpu-index 0 --json results/gate/preflight.json
#
# 退出码：0 通过 / 1 连不上或环境不可用 / 2 GPU 被占 / 3 CPU 或内存或磁盘压力
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_remote_common.sh"

GPU_INDEX=""
GPU_MEM_PCT=80
GPU_UTIL=50
MAX_LOAD_PER_CORE=0.7
MIN_FREE_MEM_MB=8000
MIN_FREE_DISK_GB=5
JSON_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gpu-index) GPU_INDEX="$2"; shift 2 ;;
    --gpu-mem-pct) GPU_MEM_PCT="$2"; shift 2 ;;
    --gpu-util) GPU_UTIL="$2"; shift 2 ;;
    --max-load-per-core) MAX_LOAD_PER_CORE="$2"; shift 2 ;;
    --min-free-mem-mb) MIN_FREE_MEM_MB="$2"; shift 2 ;;
    --min-free-disk-gb) MIN_FREE_DISK_GB="$2"; shift 2 ;;
    --json) JSON_PATH="$2"; shift 2 ;;
    --help|-h) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
done

GUARD_ARGS=(preflight --gpu-mem-pct "$GPU_MEM_PCT" --gpu-util "$GPU_UTIL"
            --max-load-per-core "$MAX_LOAD_PER_CORE"
            --min-free-mem-mb "$MIN_FREE_MEM_MB" --min-free-disk-gb "$MIN_FREE_DISK_GB")
[[ -n "$GPU_INDEX" ]] && GUARD_ARGS+=(--gpu-index "$GPU_INDEX")

echo "### 容量预检（${REMOTE}）"
RC=255
for attempt in 1 2 3; do
  ssh "${SSH_OPTS[@]}" "$REMOTE" "bash -s -- ${GUARD_ARGS[*]}" < "$SCRIPT_DIR/resource_guard.sh"
  RC=$?
  [[ "$RC" != 255 ]] && break
  echo "  ssh 连接失败（第 $attempt 次），5s 后重试..."
  sleep 5
done

if ! [[ "$RC" =~ ^[0-9]+$ ]] || (( RC == 255 )); then
  die "无法连接 $REMOTE：容量检查没有运行，不能当作通过"
fi

if [[ -n "$JSON_PATH" ]]; then
  mkdir -p "$(dirname "$JSON_PATH")"
  printf '{"time":"%s","remote":"%s","exit_code":%d,"gpu_index":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REMOTE" "$RC" "${GPU_INDEX:-all}" > "$JSON_PATH"
  echo "  预检结果 → $JSON_PATH"
fi

case "$RC" in
  0) echo "### PREFLIGHT OK"; exit 0 ;;
  2) echo "### 拒绝：GPU 被占用（退出码 2）—— 停下来问用户，不许抢" >&2; exit 2 ;;
  3) echo "### 拒绝：CPU/内存/磁盘压力（退出码 3）" >&2; exit 3 ;;
  *) echo "### 拒绝：环境不可用（退出码 $RC）" >&2; exit 1 ;;
esac
