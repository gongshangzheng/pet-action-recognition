---
name: repo-structure
description: Use when asked how the pet-action-recognition repo is organized — where a file or feature lives, what each top-level directory does, how frontend/backend/data/training fit together, or before navigating an unfamiliar part of the codebase. Triggers (CN+EN): "文件组织", "目录结构", "项目结构", "这个库怎么搭的", "某文件在哪", "X 放在哪个目录", "codebase layout", "repository structure", "where does X live".
---

# 仓库结构 / Repo Structure

## 这是什么
pet-action-recognition 仓库的**导航地图**。一句话定位每个顶层目录的职责、前后端 / 数据 / 训练如何拼在一起，并指明要"做"某件事时该切到哪个模块 skill。

## 何时用 / When to use
- 被问"这个库怎么组织的 / 目录结构 / 项目结构 / 某文件在哪 / codebase layout"
- 进入不熟悉的模块前，想先建立全局图
- 决定一个**新文件该放哪**
- **不该用**：要在某个模块里做 CRUD / 跑训练 / 开发页面 —— 直接用对应模块 skill（见「模块路由」表）

## 顶层布局

```
pet-action-recognition/
├── server/                     # FastAPI 后端（:8788）
│   ├── main.py                 # 入口；config.py = 端口/CORS/DB 路径
│   ├── db.py                   # 论文 SQLite 操作
│   ├── routers/                # papers / management / evaluation / training
│   ├── parsers/                # management/ Markdown 解析器（tasks/team/report/milestones/projects/markdown_table）
│   └── utils/file_utils.py
├── web/                        # Vue3 + Vite + Naive UI 前端（:3000，代理 /api → 8788）
│   └── src/{api, views, components, layouts, router, stores, styles, assets}
│        └── views/{papers, management, evaluation, training}
├── management/                 # 项目管理 Markdown（team/daily/weekly/monthly/docs）—— 后端直接读写
├── papers/                     # 论文搜集（config/docs/scripts；data、cache 已 gitignore）
├── evaluation/                 # 评测（configs/datasets/models/outputs/scripts）
├── datasets/quadruped_action/  # 四足动作数据集清单（train/val/test list + classes.txt）
├── results/training/           # 训练运行时产物（checkpoints/、logs/；大多 gitignore）
├── models/mmaction2/      # vendored 训练框架（只读快照，别直接改；升级走 using-mmaction2）
├── scripts/                    # 顶层脚本：train_model / inference / run_test / import_papers / export_papers / generate_synthetic_quadruped
├── data/                       # 运行时数据：extracted_papers.json（导入源）、papers.db（SQLite，gitignore）
├── docs/plans/                 # 计划文档（如 mmaction2 训练集成方案）
├── .claude/{agents,skills}     # 项目级 skill 与 agent（随仓库版本管理）
├── AGENTS.md                   # 权威架构说明（技术栈/服务架构/目录结构/开发规范）
├── README.md                   # 面向人的项目说明 + 项目结构
└── start_services.sh           # 一键启动（后端 8788 + 前端 3000）
```

## 请求流 / Request flow

```
浏览器 → Vite(:3000, 代理 /api) → FastAPI(:8788) → SQLite(data/papers.db)
                                              ↘ FastAPI → management/ Markdown 读写
                                              ↘ FastAPI → datasets/ + results/training/（训练/推理）
```

- **前端**：Vue3 SPA，Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI（Python 3.9），直接操作 SQLite，同时读写 `management/` 下 Markdown
- **DB**：本地 SQLite，独立于任何外部服务

## 模块路由（要"做"事，切到对应 skill）

| 任务 | Skill |
|------|-------|
| 训练 / 推理 / 升级 mmaction2 | using-mmaction2 |
| 评测模型 / 数据集 / 跑评测 | evaluation |
| 论文导入 / 分类 / 笔记 | papers |
| 团队 / 报表 / 任务 / 会议 CRUD | management |
| 前后端开发 / 启动 / 调试 | web |
| 上游 / 下游四库 git 同步 | upstream-sync |

## 权威来源（需要更细时去读）
- **`AGENTS.md`** ——「目录结构 / 服务架构 / 开发规范」；AI agent 的主参考，最全
- **`README.md`** ——「项目结构」段，面向人
- **`management/docs/projects/pet-action-recognition/README.md`** ——「项目树」进展（持续更新）

## 常见坑
- `models/mmaction2/` 是 **vendored 快照**，不要在仓库里直接改它；升级走 using-mmaction2 的 vendor 流程
- **项目级 skill 必须放 `.claude/skills/`**（随仓库走），不要放 `~/.claude/skills/`（那是跨项目通用 skill）
- `data/papers.db`、`results/training/work_dirs/`、`papers/data/`、`papers/cache/` 已 gitignore —— 换机器需重新生成/导入
- 后端是 **Python 3.9**：类型注解用 `Optional[str]`，不要用 `str | None`
- 目录树可能滞后于实际代码；以 `AGENTS.md` + 实际 `ls` 为准
