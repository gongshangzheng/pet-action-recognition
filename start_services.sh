#!/bin/bash
cd /Users/tangwen/pet-action-recognition
python3 -c "import sys; sys.path.insert(0,'.'); import uvicorn; from server.main import app; uvicorn.run(app, host='0.0.0.0', port=8080)" > /tmp/backend.log 2>&1 &
cd /Users/tangwen/pet-action-recognition/web
npx vite --port 3000 --strict-port > /tmp/frontend.log 2>&1 &
sleep 5
echo "Backend: $(curl -s --max-time 3 http://localhost:8080/api/health)"
echo "Frontend: $(curl -s --max-time 3 http://localhost:3000 | head -c 60)"
echo "Proxy: $(curl -s --max-time 3 http://localhost:3000/api/management/team | head -c 80)"
