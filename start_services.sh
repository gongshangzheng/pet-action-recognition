#!/bin/bash
# 启动 ProjFlow 项目管理平台全部服务
# 端口分配：后端=8090  前端=3002

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- 1. Backend (port 8090) ---
if lsof -i :8090 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Backend (8090) already running"
else
  echo "Starting Backend (8090)..."
  cd "$BASE_DIR"
  nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090 </dev/null > /tmp/projflow-backend.log 2>&1 & disown
  sleep 2
fi

# --- 2. Frontend (port 3002) ---
if lsof -i :3002 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Frontend (3002) already running"
else
  echo "Starting Frontend (3002)..."
  cd "$BASE_DIR/web"
  nohup npx vite --port 3002 --strict-port </dev/null > /tmp/projflow-frontend.log 2>&1 & disown
  sleep 3
fi

# --- 验证 ---
echo ""
echo "=== Service Status ==="
echo "Backend   (8090): $(curl -s --max-time 3 http://localhost:8090/api/health | head -c 60)"
echo "Frontend  (3002): $(curl -s --max-time 3 http://localhost:3002 | head -c 40)"
