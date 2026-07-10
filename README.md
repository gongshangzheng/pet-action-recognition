# ProjFlow

通用项目管理 demo 平台——项目管理、论文搜集、评测体系三大模块。

## 项目背景

ProjFlow 是一个轻量级项目管理平台 demo，适用于小型团队的日常协作管理。基于 Markdown 文件和 SQLite 存储数据，开箱即用。

核心功能：
- **项目管理**：成员档案、技能特长、日报/周报/月报、任务看板、里程碑、会议纪要
- **论文搜集**：多源聚合、智能分类、精读笔记
- **评测体系**：模型管理、数据集管理、评测运行、结果对比

## 项目结构

```
ProjFlow/
├── management/      # 项目管理体系
│   ├── team/        # 团队成员档案
│   ├── daily/       # 日报
│   ├── weekly/      # 周报
│   ├── monthly/     # 月报
│   └── docs/        # 任务、里程碑、会议纪要
├── papers/          # 论文搜集模块
│   ├── config/      # 数据源配置
│   ├── data/        # 论文数据
│   ├── cache/       # 缓存
│   └── scripts/     # 脚本
├── evaluation/      # 评测体系模块
│   ├── models/      # 模型定义
│   ├── datasets/    # 数据集定义
│   ├── configs/     # 评测配置
│   └── results/     # 评测结果
├── data/            # 数据目录（papers.db）
├── scripts/         # 工具脚本
├── server/          # FastAPI 后端
│   ├── routers/     # API 路由
│   ├── parsers/     # Markdown 解析器
│   └── utils/       # 工具函数
├── web/             # Vue 3 前端
│   └── src/
│       ├── api/     # API 请求封装
│       ├── views/   # 页面组件
│       ├── layouts/ # 布局组件
│       └── router/  # 路由配置
├── docs/            # 其他文档
├── AGENTS.md        # AI Agent 指南
└── start_services.sh # 一键启动脚本
```

## 快速开始

```bash
# 一键启动（后端 8090 + 前端 3002）
bash start_services.sh

# 或手动启动：
# 1. 后端
cd ProjFlow
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090

# 2. 前端
cd ProjFlow/web
npx vite --port 3002
```

启动后访问 http://localhost:3002

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | Vue 3 + Vite + Naive UI + Vue Router | 3002 |
| 后端 | FastAPI (Python) | 8090 |
| 数据源 | Markdown 文件 + SQLite | — |

## License

MIT
