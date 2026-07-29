#!/usr/bin/env bash
# reconnect_tunnel.sh — 重建 SSH 隧道（autossh 端口转发 3000+8788）
#
# 用法：bash .claude/skills/remote-servers/scripts/reconnect_tunnel.sh
#
# 当浏览器 3000 端口连不上、或 API 8788 断联时运行此脚本。
# 会：杀旧 autossh → 建 autossh 隧道 → 验证两端可达。
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
LOCAL_WEB="${PET_WEB_PORT:-3000}"
LOCAL_API="${PET_API_PORT:-8788}"
REMOTE_WEB=3000
REMOTE_API=8788
ALIVE_INTERVAL=20
ALIVE_COUNT=3

echo "[1/3] 清理旧隧道..."
pkill -f "autossh.*${LOCAL_WEB}" 2>/dev/null || true
pkill -f "ssh -L ${LOCAL_WEB}" 2>/dev/null || true
sleep 1

echo "[2/3] 启动 autossh 隧道 (${LOCAL_WEB}→${REMOTE_WEB}, ${LOCAL_API}→${REMOTE_API})..."
AUTOSSH_GATETIME=0 autossh -M 0 \
  -L ${LOCAL_WEB}:localhost:${REMOTE_WEB} \
  -L ${LOCAL_API}:localhost:${REMOTE_API} \
  "${SSH_ALIAS}" -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=${ALIVE_INTERVAL} \
  -o ServerAliveCountMax=${ALIVE_COUNT} &
disown
sleep 3

echo "[3/3] 验证..."
WEB=$(curl -s --noproxy '*' -o /dev/null -w "%{http_code}" "http://localhost:${LOCAL_WEB}/pet-action-recognition/" 2>/dev/null || echo "000")
API=$(curl -s --noproxy '*' -o /dev/null -w "%{http_code}" "http://localhost:${LOCAL_API}/api/health" 2>/dev/null || echo "000")

if [ "$WEB" = "200" ] && [ "$API" = "200" ]; then
  echo "✅ 隧道就绪: web=${WEB} api=${API}"
  echo "   浏览器: http://localhost:${LOCAL_WEB}/pet-action-recognition/"
else
  echo "❌ 隧道异常: web=${WEB} api=${API}"
  echo "   可能 SSH 连不上 pet → bash scripts/pet_repin.sh 先重 pin IP"
  exit 1
fi
