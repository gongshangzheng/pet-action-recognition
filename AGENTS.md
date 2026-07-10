# AGENTS.md — ProjFlow 项目管理平台

> 本文件供 AI Agent（如 Qoder、Cursor 等）阅读，用于理解项目架构、开发规范和工作流程。

## 项目概述

ProjFlow 是一个通用的项目管理 demo 平台，包含三大模块：**项目管理**（团队、日报/周报/月报、任务看板、里程碑、会议纪要）、**论文搜集**（多源聚合、智能分类、精读笔记）、**评测体系**（模型管理、评测运行、结果对比）。前后端分离架构，后端读写本地 Markdown 文件和 SQLite 数据库。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | Vue 3 + Vite + Naive UI + Vue Router | 3002 |
| 后端 | FastAPI (Python) | 8090 |

### 服务架构

```
浏览器 → Vite (3002) → FastAPI (8090) → management/ 目录（Markdown 文件）
                                      → data/papers.db（SQLite 论文数据库）
                                      → evaluation/ 目录（模型/数据集/结果 JSON）
```

- **前端**：Vue 3 SPA，通过 Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，三大模块各自有独立路由和数据源
- **数据源**：管理模块读写 Markdown 文件，论文模块使用 SQLite，评测模块使用 JSON 文件

## 启动服务

```bash
# 一键启动（后端 8090 + 前端 3002）
bash start_services.sh

# 或手动启动：
# 1. 后端
cd ProjFlow
nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090 </dev/null > /tmp/backend.log 2>&1 & disown

# 2. 前端
cd ProjFlow/web
nohup npx vite --port 3002 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
```

## 目录结构

```
ProjFlow/
├── AGENTS.md                # 本文件
├── .gitignore
├── start_services.sh        # 一键启动脚本
├── server/                  # FastAPI 后端
│   ├── config.py            # 配置（端口、CORS、各模块路径）
│   ├── main.py              # 入口（注册 management/papers/evaluation 路由）
│   ├── db.py                # SQLite 数据库操作（论文模块）
│   ├── routers/
│   │   ├── management.py    # 管理路由（读写 Markdown 文件）
│   │   ├── papers.py        # 论文路由（读写 SQLite）
│   │   └── evaluation.py    # 评测路由（读写 JSON）
│   ├── parsers/             # Markdown 解析器
│   │   ├── markdown_table.py    # 通用表格解析
│   │   ├── team_parser.py       # 团队成员解析
│   │   ├── report_parser.py     # 日报/周报/月报解析
│   │   ├── tasks_parser.py      # 任务看板解析
│   │   └── milestones_parser.py # 里程碑解析
│   ├── utils/
│   │   └── file_utils.py   # 文件操作工具
│   └── requirements.txt
├── web/                     # Vue 3 前端
│   ├── vite.config.js       # Vite 配置（端口 3002，代理 /api → 8090）
│   ├── src/
│   │   ├── api/             # API 请求封装（management.js, papers.js, evaluation.js）
│   │   ├── layouts/         # 布局组件
│   │   ├── router/          # 路由配置
│   │   ├── views/
│   │   │   ├── management/  # 团队、日报、周报、月报、任务看板、里程碑、会议纪要
│   │   │   ├── papers/      # 论文列表、论文详情、数据源配置
│   │   │   └── evaluation/  # 评测运行、评测结果、模型管理、数据集管理
│   │   └── components/      # 通用组件
│   └── package.json
├── management/              # 项目管理 Markdown 文件
│   ├── team/                # 团队成员档案
│   ├── daily/               # 日报
│   ├── weekly/              # 周报
│   ├── monthly/             # 月报
│   └── docs/                # 任务、里程碑、会议纪要
├── papers/                  # 论文模块
│   ├── config/              # 数据源配置
│   ├── data/                # 论文数据（.gitignore）
│   ├── cache/               # 缓存（.gitignore）
│   ├── docs/                # 文档
│   └── scripts/             # 脚本
├── evaluation/              # 评测模块
│   ├── models/              # 模型定义 JSON
│   ├── datasets/            # 数据集定义 JSON
│   ├── configs/             # 评测配置 JSON
│   ├── scripts/             # 评测脚本
│   └── results/             # 评测结果 JSON（.gitignore）
├── data/                    # 数据目录
│   └── papers.db            # SQLite 论文数据库（.gitignore）
├── scripts/                 # 工具脚本
│   └── import_papers.py     # 论文导入脚本
└── docs/                    # 其他文档
```

## 三大模块架构

### 1. 项目管理模块

**数据流**：
```
management/ 目录（Markdown 文件）
  ↓ FastAPI (port 8090, server/routers/management.py → server/parsers/)
前端 Vue 组件 (port 3002)
```

**关键设计**：
- **团队成员**：从 `management/team/README.md` 解析成员列表表格，从 `management/team/{姓名}.md` 解析成员详情（含技能特长/技术栈）
- **日报/周报/月报**：按目录结构扫描 Markdown 文件，从文件名解析日期和作者
- **任务看板**：解析 `management/docs/tasks.md` 中的三个表格（进行中、待开始、已完成）
- **里程碑**：解析 `management/docs/milestones.md` 中的表格
- **会议纪要**：扫描 `management/docs/meetings/` 目录下的 Markdown 文件

### 2. 论文搜集模块

**数据流**：
```
data/papers.db（SQLite 数据库）
  ↓ FastAPI (port 8090, server/routers/papers.py → server/db.py)
前端 Vue 组件 (port 3002)
```

**关键设计**：
- **论文存储**：SQLite 数据库 `data/papers.db`，表结构含标题、作者、摘要、来源、分类等
- **数据导入**：`scripts/import_papers.py` 脚本从 JSON 导入论文数据
- **API 端点**：论文列表（分页/筛选）、详情、统计摘要、数据源配置

### 3. 评测体系模块

**数据流**：
```
evaluation/ 目录（JSON 文件）
  ↓ FastAPI (port 8090, server/routers/evaluation.py)
前端 Vue 组件 (port 3002)
```

**关键设计**：
- **模型管理**：`evaluation/models/` 下的 JSON 文件定义模型信息
- **数据集管理**：`evaluation/datasets/` 下的 JSON 文件定义数据集信息
- **评测配置**：`evaluation/configs/` 下的 JSON 文件定义评测参数
- **评测结果**：`evaluation/results/` 下的 JSON 文件存储评测结果
- **空数据策略**：当目录为空时返回空列表（DEFAULT_MODELS 和 DEFAULT_DATASETS 均为空）

### 文件命名规范

| 类型 | 路径格式 | 示例 |
|------|----------|------|
| 日报 | `daily/YYYY/MM/DD-姓名.md` | `daily/2026/07/09-张三.md` |
| 周报 | `weekly/YYYY/WXX-姓名.md` | `weekly/2026/W28-张三.md` |
| 月报 | `monthly/YYYY/MM-姓名.md` | `monthly/2026/07-张三.md` |
| 会议 | `docs/meetings/YYYY-MM-DD.md` | `docs/meetings/2026-07-09.md` |

## 开发规范

### Git 工作流

1. **每次功能变更都应提交**，不要积累大量未提交变更
2. **提交信息格式**：`<type>: <描述>`，如 `feat: 添加任务筛选`、`fix: 修复分页问题`
3. **type 取值**：feat（新功能）、fix（修复）、refactor（重构）、style（样式）、docs（文档）、chore（杂项）
4. **禁止提交**：`node_modules/`、`__pycache__/`、`.venv/`、`.env`、`*.db`、`papers/data/`、`papers/cache/`

### 前端开发

- 框架：Vue 3 `<script setup>` + Naive UI 组件库
- 样式：SCSS，组件内 `<style scoped>`
- API 请求：通过 `web/src/api/` 封装，统一使用 `request.js` 中的 axios 实例
- 路由：`web/src/router/index.js`
- 布局：`web/src/layouts/MainLayout.vue`（侧边栏 + 内容区，`native-scrollbar=false`）

### 后端开发

- 框架：FastAPI，路由在 `server/routers/`
- 配置：`server/config.py`（端口、CORS、各模块路径）
- Markdown 解析：`server/parsers/` 目录下的解析器
- 数据库操作：`server/db.py`（论文模块 SQLite CRUD）
- Python 版本：3.9（不支持 `str | None` 语法，需用 `Optional[str]`）
- 管理路由直接读写 Markdown 文件，论文路由操作 SQLite，评测路由读写 JSON

### macOS 后台进程

```bash
# 启动后台进程（必须用 </dev/null 防止挂起）
nohup cmd </dev/null > /tmp/log 2>&1 & disown

# 检查进程
ps aux | grep <keyword> | grep -v grep

# 检查端口
lsof -i :<port>
```

## 常见问题

### 前端启动后立即挂起（进程状态为 T）
macOS 上 nohup 进程需要 `</dev/null` 重定向 stdin，否则终端关闭时进程收到 SIGHUP 挂起。

### Vite 端口被占用
使用 `--strict-port` 避免自动 fallback 到其他端口。如果 3002 被占，先 `lsof -i :3002` 找到并杀掉旧进程。

### 管理页面数据为空
检查后端（port 8090）是否在运行，`management/` 目录下是否有对应的数据文件。

### 论文页面数据为空
论文数据库 `data/papers.db` 需通过 `scripts/import_papers.py` 导入数据后才有内容。

### 评测页面数据为空
在 `evaluation/models/`、`evaluation/datasets/` 等目录下放置 JSON 文件即可显示数据。
