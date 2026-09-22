"""FastAPI 主入口 — 宠物动作识别研究平台后端"""
import sys
import os

# 确保能 import server 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.config import CORS_ORIGINS, MANAGEMENT_DIR
from server.routers import management, papers, evaluation, training, speedrun, datasets, live

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
app.include_router(speedrun.router)
app.include_router(datasets.router)
app.include_router(live.router)

# 文档图片资产仅从 management/docs/_assets/ 只读提供。
DOC_ASSETS_DIR = os.path.join(MANAGEMENT_DIR, "docs", "_assets")
os.makedirs(DOC_ASSETS_DIR, exist_ok=True)
app.mount(
    "/api/management/docs-assets",
    StaticFiles(directory=DOC_ASSETS_DIR, check_dir=False),
    name="doc-assets",
)


@app.get("/")
async def root():
    return {"message": "宠物动作识别研究平台 API", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8788, reload=True)
