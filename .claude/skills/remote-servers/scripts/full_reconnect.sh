#!/usr/bin/env bash
# full_reconnect.sh — 全量重连（隧道 + 服务）
#
# 用法：bash .claude/skills/remote-servers/scripts/full_reconnect.sh
#
# 当 SSH 频繁断连、或 frp IP 可能变了时运行。会：
# 1. 检查 SSH 连通性（不通则自动 pet_repin.sh）
# 2. 重启 pet 上的 uvicorn
# 3. 重建 autossh 隧道
# 4. 验证 web + API 都可达
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [1/4] SSH 连通性检查 ==="
if ! ssh -o ConnectTimeout=10 "${PET_ALIAS:-pet}" 'echo ok' >/dev/null 2>&1; then
  echo "SSH 不通 → 运行 pet_repin.sh"
  bash "${REPO_ROOT}/scripts/pet_repin.sh"
else
  echo "✅ SSH 通"
fi

echo "=== [2/4] 重启 pet uvicorn ==="
bash "${SCRIPT_DIR}/restart_services.sh"

echo "=== [3/4] 重建隧道 ==="
bash "${SCRIPT_DIR}/reconnect_tunnel.sh"

echo "=== [4/4] 完成 ==="
echo "浏览器: http://localhost:3000/pet-action-recognition/"
