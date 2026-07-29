#!/usr/bin/env bash
# restart_services.sh — 在 pet 上重启 uvicorn 后端
#
# 用法：bash .claude/skills/remote-servers/scripts/restart_services.sh
#
# 当 API 返回 502 或后端代码有更新（git push 后需重启 uvicorn）时运行。
set -euo pipefail

SSH_ALIAS="${PET_ALIAS:-pet}"
PYTHON="~/miniconda3/envs/pet/bin/python"
REPO="~/pet-action-recognition"
PORT="${PET_API_PORT:-8788}"

echo "[1/2] 杀旧 uvicorn + 重启..."
ssh -o ConnectTimeout=10 "${SSH_ALIAS}" \
  "pkill -f uvicorn 2>/dev/null; sleep 2; cd ${REPO} && (nohup ${PYTHON} -m uvicorn server.main:app --host 127.0.0.1 --port ${PORT} > /tmp/uv.log 2>&1 < /dev/null &); echo started"

echo "[2/2] 等待启动 + 验证..."
sleep 5
API=$(ssh -o ConnectTimeout=8 "${SSH_ALIAS}" \
  "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${PORT}/api/health" 2>/dev/null || echo "000")

if [ "$API" = "200" ]; then
  echo "✅ uvicorn 就绪: ${PORT} → ${API}"
else
  echo "❌ uvicorn 启动失败 (http=${API})"
  echo "   查日志: ssh ${SSH_ALIAS} 'tail -20 /tmp/uv.log'"
  exit 1
fi
