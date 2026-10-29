#!/bin/bash
# Shared config for every remote-interaction script. Source this file; do not execute it.
#
# Owned by the remote-ops skill: SSH target, remote checkout path and log dir are defined once here
# so no script invents its own copy. 本仓（pet-action-recognition）没有常驻服务与前端隧道，
# 因此不定义 API_BASE / TUNNEL_PORTS —— 需要时用 tunnels.sh 或在调用处显式给出。

REMOTE="${PET_REMOTE_SSH:-pet}"
SSH_OPTS=(-o ConnectTimeout=10)
REMOTE_ROOT="${PET_REMOTE_ROOT:-/home/wyy/pet-action-recognition}"
REMOTE_LOG_DIR="${REMOTE_ROOT}/results/.run_logs"

# .claude/skills/remote-ops/scripts -> repo root is four levels up
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

# 连接 pet 不走代理（本机装有全局代理时会破坏 frp 隧道）
export NO_PROXY='*'
unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy 2>/dev/null || true

ssh_cmd() {
  ssh "${SSH_OPTS[@]}" "$REMOTE" "$1"
}

die() {
  echo "ERROR: $1" >&2
  exit 1
}

port_open() {
  nc -z -w 3 localhost "$1" >/dev/null 2>&1
}
