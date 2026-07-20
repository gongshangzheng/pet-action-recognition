"""FastAPI 主入口 — 宠物动作识别研究平台后端"""
import sys
import os

# 确保能 import server 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config import CORS_ORIGINS
from server.routers import management, papers, evaluation, training

app = FastAPI(
    title="宠物动作识别研究平台 API",
    description="为前端提供项目管理、论文搜集、评测体系的数据接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(management.router)
app.include_router(papers.router)
app.include_router(evaluation.router)
app.include_router(training.router)


@app.get("/")
async def root():
    return {"message": "宠物动作识别研究平台 API", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8788, reload=True)
