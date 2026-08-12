# AGENTS.md — 宠物动作识别研究平台

> 本文件供 AI Agent 阅读，用于理解项目架构、开发规范和工作流程。

## 项目概述

宠物动作识别研究平台，用于管理动作识别相关论文、团队协作、模型训练和实时推理。

论文数据来源于博客仓库 `~/gongshangzheng.github.io` 中「AI/动作识别」分类下的 17 篇文章，从中提取了 140 篇相关论文。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | Vue 3 + Vite + Naive UI + Vue Router | 3000 |
| 后端 | FastAPI (Python) | 8788 |
| 数据库 | SQLite (data/papers.db) + JSON 文件 | — |

### 服务架构

```
浏览器 → Vite (3000) → FastAPI (8788) → SQLite (data/papers.db)
                   ↘ FastAPI → management/ (Markdown 文件)
                   ↘ FastAPI → live/ (视频流 + 截屏数据库)
                   ↘ FastAPI → results/ (训练/评测产物)
```

- **前端**：Vue 3 SPA，通过 Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，直接操作 SQLite 数据库，读写 `management/` 下的 Markdown 文件
- **Live 模块**：摄像头源管理、视频流代理、实时推理（SSE）
- **数据库**：本地 SQLite + JSON 文件，独立于任何外部服务

## 启动服务

```bash
# 一键启动（后端 8788 + 前端 3000）
bash start_services.sh

# 或手动启动：
# 1. 后端
cd ~/pet-action-recognition
nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788 </dev/null > /tmp/backend.log 2>&1 & disown

# 2. 前端
cd ~/pet-action-recognition/web
nohup npx vite --port 3000 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
```

## 目录结构

```
pet-action-recognition/
├── AGENTS.md                    # 本文件
├── .gitignore
├── start_services.sh           # 一键启动脚本
├── README.md                    # 面向人的项目说明
│
├── server/                      # FastAPI 后端（:8788）
│   ├── main.py                  # 入口，注册 8 个 router
│   ├── config.py                # 配置（端口、CORS、路径常量）
│   ├── db.py                    # 论文 SQLite 操作
│   ├── db_live.py               # Live 模块 SQLite 操作
│   ├── live/                    # Live 安全模块（stream_token）
│   ├── routers/                 # 8 个路由模块
│   │   ├── papers.py            # 论文路由
│   │   ├── management.py        # 项目管理路由（只读 Markdown）
│   │   ├── evaluation.py        # 评测路由
│   │   ├── training.py          # 训练路由（mmaction2）
│   │   ├── speedrun.py          # Speed Run 路由
│   │   ├── datasets.py          # 数据集路由
│   │   └── live.py              # Live 路由（摄像头源 + SSE 推理）
│   ├── parsers/                 # Markdown 解析器
│   └── utils/                   # 工具函数
│
├── web/                         # Vue 3 前端（:3000，代理 /api → 8788）
│   ├── vite.config.js           # Vite 配置
│   └── src/
│       ├── api/                 # API 请求封装（papers, training, live 等）
│       ├── layouts/             # 布局组件
│       ├── router/              # 路由配置
│       ├── views/
│       │   ├── Home.vue          # 首页
│       │   ├── Live.vue          # 实时视频流 + 推理
│       │   ├── papers/           # 论文列表、详情、数据源
│       │   ├── management/       # 团队、报表、任务、里程碑、会议、文档
│       │   ├── evaluation/       # 评测结果
│       │   ├── training/         # 训练配置、数据集、模型、运行、结果
│       │   └── datasets/         # 数据集管理
│       └── components/
│           ├── common/          # 通用组件
│           └── live/             # Live 专用组件（VideoPlayer, SourceManageModal, PtzJoystick）
│
├── configs/                     # mmaction2 训练 config（含 hooks/ 自定义 hook）
├── models/
│   └── mmaction2/               # vendored mmaction2 快照（只读，勿直接改）
│
├── datasets/                    # 数据集目录
│   └── quadruped_action/        # 四足动物动作数据集
│
├── scripts/                    # 顶层脚本
│   ├── train_model.py           # 训练包装
│   ├── run_test.py              # 正式测试
│   ├── speedrun.py              # Speed Run 批量
│   ├── inference.py             # 单视频推理
│   ├── _infer.py                # 共享推理 + cv2 标注
│   ├── download_checkpoint.py   # 下载预训练权重
│   ├── live_analyze.py          # Live SSE 推理
│   ├── vlm_infer.py             # VLM 推理
│   ├── run_test_vlm.py          # VLM 测试
│   └── ...
│
├── management/                 # 项目管理 Markdown
│   ├── team/                    # 团队成员
│   ├── daily/                   # 日报
│   ├── weekly/                 # 周报
│   ├── monthly/                # 月报
│   ├── meetings/               # 会议纪要
│   ├── milestones.md           # 里程碑
│   ├── projects/               # 项目树 + tasks.json
│   └── docs/                   # Wiki 文档
│
├── papers/                      # 论文模块（config/docs/scripts 子目录）
├── evaluation/                  # 评测模块（configs/datasets/models/outputs/scripts）
├── results/                     # 产物目录
│   ├── training/               # 训练产物（metrics.json, test_results.json, checkpoints/）
│   ├── speedrun/                # Speed Run 产物（outputs/, results.json）
│   ├── live/                   # Live 产物
│   └── skeleton/               # 骨架提取产物
├── data/                        # 运行时数据
│   ├── extracted_papers.json    # 从博客提取的论文列表
│   └── papers.db                # 论文 SQLite 数据库
├── live/                        # Live 模块数据（screenshots/）
├── checkpoints/                 # 预训练 + 训练 checkpoint（gitignore）
├── docs/                        # 设计文档
├── third-party/                 # 第三方集成（pet-videos, remix-petra）
├── .claude/                     # 项目级 skills 和 agents（随仓库版本管理）
│   └── skills/                  # 14 个 skill
└── package-lock.json
```

## 核心模块

### 1. 论文模块 (`papers/`, `server/routers/papers.py`)

- 从博客仓库提取论文，存入 SQLite
- 支持搜索/筛选/收藏/置顶/笔记
- 详情浮窗 + URL hash 持久化

### 2. 训练模块 (`training/`, `server/routers/training.py`)

- 基于 mmaction2 框架
- 支持四种训练模式（从头/预训练/加载权重/断点续训）
- 21 个 mmaction2 模型族注册
- 远程服务器执行（pet RTX 4090）

### 3. 评测模块 (`evaluation/`, `server/routers/evaluation.py`)

- 模型管理 + 数据集管理
- 正式测试（top1/top5）+ speed run
- VLM（Qwen3-VL-Plus）集成
- 结果对比

### 4. Live 模块 (`live/`, `server/routers/live.py`)

- 摄像头源 CRUD（stream_url + storage_path）
- 视频流代理（stream_token 安全签名）
- SSE 实时推理（逐段输出 top-k + 状态）
- 截屏上传管理

### 5. 项目管理模块 (`management/`, `server/routers/management.py`)

- 团队成员、日报/周报/月报
- 任务看板、里程碑、会议纪要
- Wiki 文档
- **后端只读**，脚本直接改文件

## 数据库结构

### papers 表
```sql
id, title, title_zh, abstract, abstract_zh, authors (JSON),
published_at, crawled_at, url, pdf_url, source, external_ids (JSON),
summary_zh, relevance_score, llm_classification (JSON), metadata (JSON),
arxiv_categories (JSON), starred (int), pinned (int), blog_url, note
```

**注意**：`authors` 字段是 JSON 数组字符串（如 `["Author A", "Author B"]`），`server/db.py` 用 `json.loads()` 解析。

### Live 模块（db_live.py）
```sql
-- stream_sources 表
id, name, alias, stream_url, storage_path, is_active, created_at, updated_at

-- screenshots 表
id, source_id, filename, note, created_at
```

## 开发规范

### Git 工作流

1. **每次功能变更都应提交**，不要积累大量未提交变更
2. **提交信息格式**：`<type>: <描述>`
3. **type 取值**：feat（新功能）、fix（修复）、refactor（重构）、style（样式）、docs（文档）、chore（杂项）
4. **禁止提交**：`node_modules/`、`__pycache__/`、`.venv/`、`*.db`、`data/papers.db`、`results/`、`checkpoints/`、`live/screenshots/`

### 前端开发

- 框架：Vue 3 `<script setup>` + Naive UI 组件库
- 样式：SCSS，组件内 `<style scoped>`
- API 请求：通过 `web/src/api/` 封装
- 路由：`web/src/router/index.js`
- 布局：`web/src/layouts/MainLayout.vue`

### 后端开发

- 框架：FastAPI，路由在 `server/routers/`
- 配置：`server/config.py`
- 数据库：`server/db.py`（论文）、`server/db_live.py`（Live）
- Python 版本：`python3` 3.13
- 管理路由直接读写 Markdown 文件

### Skill 管理

- **项目级 skill 放在 `.claude/skills/`**（随仓库版本管理）
- **跨项目通用 skill 放在 `~/.claude/skills/`**
- `.agents/` 是 `.claude/` 的软链接

### 当前项目 Skill（15 个）

| Skill | 路径 | 用途 |
|-------|------|------|
| repo-structure | `.claude/skills/repo-structure/` | 仓库文件组织、目录结构、模块路由 |
| datasets | `.claude/skills/datasets/` | 数据集与预训练权重管理 |
| design-principles | `.claude/skills/design-principles/` | UI/UX 设计原则 |
| documentation | `.claude/skills/documentation/` | 文档写作指南 |
| evaluation | `.claude/skills/evaluation/` | 评测体系模块（mmaction2 动作识别） |
| live | `.claude/skills/live/` | 实时视频流 + SSE 推理 |
| management | `.claude/skills/management/` | 项目管理 CRUD |
| papers | `.claude/skills/papers/` | 论文收集模块 |
| remote-servers | `.claude/skills/remote-servers/` | 远程服务器使用 |
| testing | `.claude/skills/testing/` | 测试/speed run/推理 |
| training | `.claude/skills/training/` | mmaction2 训练 |
| upstream-sync | `.claude/skills/upstream-sync/` | 上下游仓库同步 |
| using-mmaction2 | `.claude/skills/using-mmaction2/` | mmaction2 深度指南 |
| web | `.claude/skills/web/` | Web 全栈开发 |
|  |  |  |

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
macOS 上 nohup 进程需要 `</dev/null` 重定向 stdin。

### Vite 端口被占用
使用 `--strict-port` 避免自动 fallback 到其他端口。

### 论文列表为空
检查后端（port 8788）是否在运行，`data/papers.db` 是否存在且有数据。

### 训练/测试必须在远程服务器
**绝不在本地跑训练、测试、推理**（本地无 GPU）。所有 GPU 活必须在 pet（RTX 4090）或 A100 上执行。
