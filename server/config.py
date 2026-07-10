import os

# 仓库根目录（server/ 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各模块路径
MANAGEMENT_DIR = os.path.join(BASE_DIR, "management")
PAPERS_DIR = os.path.join(BASE_DIR, "papers")
EVALUATION_DIR = os.path.join(BASE_DIR, "evaluation")

# 论文数据库路径（本地独立数据库）
PAPERS_DB = os.path.join(BASE_DIR, "data", "papers.db")

# CORS 配置
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
