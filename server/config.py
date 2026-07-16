import os

# 仓库根目录（server/ 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各模块路径
MANAGEMENT_DIR = os.path.join(BASE_DIR, "management")
PAPERS_DIR = os.path.join(BASE_DIR, "papers")
EVALUATION_DIR = os.path.join(BASE_DIR, "evaluation")

# 评测输出目录（压缩码流 / 重建视频等，供 /api/evaluation/outputs 端点按需服务）
# 下游库可覆盖：infraredComp 用 results/video/，其它库用 evaluation/outputs/
OUTPUTS_DIR = os.path.join(EVALUATION_DIR, "outputs")

# 训练模块路径（镜像 results/video/ 结构）
# 下游库可覆盖：infraredComp 用 results/training/，其它库用 training/outputs/
TRAINING_DIR = os.path.join(BASE_DIR, "results", "training")
TRAINING_METRICS_JSON = os.path.join(TRAINING_DIR, "metrics.json")  # 训练 run 列表(含 loss_series)
CHECKPOINTS_DIR = os.path.join(TRAINING_DIR, "checkpoints")         # trained .pth state_dicts
TRAINING_LOGS_DIR = os.path.join(TRAINING_DIR, "logs")              # 训练日志
# 训练产物服务根目录（checkpoint + log 文件，供 /api/training/outputs 按需服务）
TRAINING_OUTPUTS_DIR = TRAINING_DIR

# 四足动物动作数据集（名称未定，先设为变量；数据集收集后改这一处即可）
# datasets/<QUADRUPED_DATASET_NAME>/ 为训练/评测共用根目录
QUADRUPED_DATASET_NAME = "quadruped_action"
QUADRUPED_DATASET_DIR = os.path.join(BASE_DIR, "datasets", QUADRUPED_DATASET_NAME)

# 论文数据库路径（本地独立数据库）
PAPERS_DB = os.path.join(BASE_DIR, "data", "papers.db")

# CORS 配置
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
