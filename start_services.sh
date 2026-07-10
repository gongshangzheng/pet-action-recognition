#!/bin/bash
# 启动宠物动作识别研究平台全部服务
# 端口分配：后端=8080  前端=3000
# 论文数据库：data/papers.db（本地 SQLite，独立于 SeekVerse）

BASE_DIR=/Users/tangwen/pet-action-recognition

# --- 1. Backend (port 8080) ---
if lsof -i :8080 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Backend (8080) already running"
else
  echo "Starting Backend (8080)..."
  cd "$BASE_DIR"
  nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080 </dev/null > /tmp/backend.log 2>&1 & disown
  sleep 2
fi

# --- 2. Frontend (port 3000) ---
if lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Frontend (3000) already running"
else
  echo "Starting Frontend (3000)..."
  cd "$BASE_DIR/web"
  nohup npx vite --port 3000 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
  sleep 3
fi

# --- 验证 ---
echo ""
echo "=== Service Status ==="
echo "Backend   (8080): $(curl -s --max-time 3 http://localhost:8080/api/papers/stats/summary | head -c 60)"
echo "Frontend  (3000): $(curl -s --max-time 3 http://localhost:3000 | head -c 40)"
