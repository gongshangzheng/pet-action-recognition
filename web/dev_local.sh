#!/bin/bash
# 本地前端开发模式：vite dev 3000（前端本地秒开）+ ssh 隧道 8788（pet 后端）
# 用法：bash web/dev_local.sh
# 访问 http://localhost:3000/pet-action-recognition/
#
# 为什么不直接用 pet 上的 vite：vite dev 按需加载 36+ 模块，每个过 frp 隧道 100-200ms，
# 页面加载 3s+。本地 vite 模块在本地无 frp 延迟，domContentLoaded ~240ms。
# pet 只跑后端（8788），数据 API 经隧道（少量、小）。

set -e
cd "$(dirname "$0")/.."  # 仓库根

# 1. 清旧隧道（8788）+ 本地 vite
pkill -f "ssh.*-L.*8788" 2>/dev/null || true
pkill -f "vite.*--port 3000" 2>/dev/null || true
sleep 1

# 2. 起 ssh 隧道 8788 → pet 后端（autossh 保活，断了自动重连）
if command -v autossh >/dev/null 2>&1; then
  AUTOSSH_GATETIME=0 autossh -M 0 -f -L 8788:localhost:8788 pet -N \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3
else
  ssh -fN -L 8788:localhost:8788 pet -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3
fi
echo "✓ ssh 隧道 8788 → pet 后端"

# 3. 验证后端
if curl -s --max-time 8 -o /dev/null -w "" http://localhost:8788/api/health; then
  echo "✓ pet 后端可达"
else
  echo "✗ pet 后端不通，先 ssh pet 起后端：~/miniconda3/envs/pet/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 8788 &"
  exit 1
fi

# 4. 本地 vite dev 3000（前台，Ctrl+C 停）
echo "→ 启动本地 vite dev :3000 ..."
cd web
npx vite --port 3000 --strict-port
