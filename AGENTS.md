# AGENTS.md — 宠物动作识别研究平台

> 本文件供 AI Agent（如 Qoder、Cursor 等）阅读，用于理解项目架构、开发规范和工作流程。

## 项目概述

宠物动作识别研究平台，用于管理动作识别相关论文、团队协作和模型评估。

论文数据来源于博客仓库 `~/gongshangzheng.github.io` 中「AI/动作识别」分类下的 17 篇文章，从中提取了 140 篇相关论文。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | Vue 3 + Vite + Naive UI + Vue Router | 3000 |
| 后端 | FastAPI (Python) | 8080 |
| SeekVerse | 外部论文管理服务（SQLite） | 8000 |

### 服务依赖关系

```
浏览器 → Vite (3000) → FastAPI (8080) → SeekVerse (8000) → SQLite (~/seekverse/data/seekverse.db)
                   ↘ FastAPI (8080) → management/ 目录（Markdown 文件读写）
```

- **前端**：Vue 3 SPA，通过 Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，代理论文相关请求到 SeekVerse，同时直接读写 `management/` 下的 Markdown 文件
- **SeekVerse**：独立服务，管理论文数据库（SQLite），提供论文 CRUD、缩略图、笔记等 API

## 启动服务

```bash
# 1. 启动 SeekVerse（外部依赖）
cd ~/seekverse && .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &

# 2. 启动后端
cd ~/pet-action-recognition
nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080 </dev/null > /tmp/backend.log 2>&1 & disown

# 3. 启动前端
cd ~/pet-action-recognition/web
nohup npx vite --port 3000 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
```

或使用一键脚本：`bash start_services.sh`

## 目录结构

```
pet-action-recognition/
├── AGENTS.md                # 本文件
├── .gitignore
├── start_services.sh        # 一键启动脚本
├── server/                  # FastAPI 后端
│   ├── config.py            # 配置（端口、CORS、SeekVerse 地址）
│   ├── main.py              # 入口
│   ├── routers/
│   │   ├── papers.py        # 论文路由（代理 SeekVerse + 本地收藏/置顶）
│   │   ├── management.py    # 管理路由（读写 Markdown 文件）
│   │   └── evaluation.py    # 评估路由
│   ├── parsers/             # Markdown 解析器
│   └── requirements.txt
├── web/                     # Vue 3 前端
│   ├── vite.config.js       # Vite 配置（端口 3000，代理 /api → 8080）
│   ├── src/
│   │   ├── api/             # API 请求封装
│   │   ├── layouts/         # 布局组件
│   │   ├── router/          # 路由配置
│   │   ├── views/
│   │   │   ├── papers/      # 论文列表、详情、数据源配置
│   │   │   ├── management/  # 日报、周报、月报、任务看板、团队、里程碑
│   │   │   └── evaluation/  # 模型管理、数据集、评估运行、结果
│   │   └── components/      # 通用组件
│   └── package.json
├── data/                    # 运行时数据
│   ├── extracted_papers.json   # 从博客提取的论文列表（导入源）
│   └── paper_favorites.json    # 收藏/置顶状态
├── scripts/
│   └── import_papers.py     # 论文导入脚本（从 arXiv API 获取元数据写入 SeekVerse DB）
├── management/              # 团队管理 Markdown 文件
├── papers/                  # 论文相关资料
├── evaluation/              # 模型评估
└── docs/                    # 文档
```

## 论文模块架构

### 数据流

```
博客文章 (~/gongshangzheng.github.io/src/pages/)
  ↓ scripts/import_papers.py 提取论文信息
data/extracted_papers.json (140 篇)
  ↓ 从 arXiv API 获取元数据
SeekVerse SQLite DB (~/seekverse/data/seekverse.db)
  ↓ SeekVerse API (port 8000)
FastAPI 代理 (port 8080, server/routers/papers.py)
  ↓ 附加本地收藏/置顶状态
前端 PaperList.vue (port 3000)
```

### 关键设计

- **论文列表**：代理 SeekVerse API，附加本地 `data/paper_favorites.json` 中的收藏/置顶状态
- **论文详情**：浮窗模式（n-modal），URL hash `#paper={id}` 持久化，刷新后恢复浮窗和滚动位置
- **筛选**：搜索 + 时间下拉 + 分类下拉（左侧）；收藏开关 + 排序符号按钮 ↓↑Aa（右侧）
- **排序**：置顶论文始终在最前，其余按选定方式排列
- **缩略图**：通过后端代理 SeekVerse，需检查 content-type 防止 JSON 错误响应当作图片

### SeekVerse 数据库结构

```sql
-- papers 表
id, title, title_zh, abstract, abstract_zh, authors (JSON array),
published_at, crawled_at, url, pdf_url, source, external_ids (JSON),
summary_zh, relevance_score, llm_classification (JSON), metadata (JSON),
arxiv_categories (JSON), starred, pinned

-- paper_categories 表
paper_id, category, confidence
```

**注意**：`authors` 字段是 JSON 数组字符串（如 `["Author A", "Author B"]`），不是逗号分隔的纯文本。SeekVerse 的 `_row_to_paper` 用 `json.loads()` 解析。

## 开发规范

### Git 工作流

1. **每次功能变更都应提交**，不要积累大量未提交变更
2. **提交信息格式**：`<type>: <描述>`，如 `feat: 添加论文收藏开关`、`fix: 修复缩略图代理 content-type 检查`
3. **type 取值**：feat（新功能）、fix（修复）、refactor（重构）、style（样式）、docs（文档）、chore（杂项）
4. **禁止提交**：`node_modules/`、`__pycache__/`、`.venv/`、`*.db`、`.env`

### 前端开发

- 框架：Vue 3 `<script setup>` + Naive UI 组件库
- 样式：SCSS，组件内 `<style scoped>`
- API 请求：通过 `web/src/api/` 封装，统一使用 `request.js` 中的 axios 实例
- 路由：`web/src/router/index.js`
- 布局：`web/src/layouts/MainLayout.vue`（侧边栏 + 内容区，`native-scrollbar=false`）

### 后端开发

- 框架：FastAPI，路由在 `server/routers/`
- 配置：`server/config.py`（端口、CORS、SeekVerse 地址）
- 论文路由代理 SeekVerse，管理路由直接读写 Markdown 文件
- 收藏/置顶状态存储在 `data/paper_favorites.json`

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
使用 `--strict-port` 避免自动 fallback 到其他端口。如果 3000 被占，先 `lsof -i :3000` 找到并杀掉旧进程。

### SeekVerse 缩略图返回 JSON 而非图片
SeekVerse 在缩略图不存在时返回 200 状态码但 body 是 JSON 错误信息。代理时必须检查 `content-type` 是否包含 `image`。

### 论文列表为空
优先检查 SeekVerse（port 8000）是否在运行，后端（port 8080）是否能连通 SeekVerse。

### 论文导入后 API 报 500
检查 `authors` 字段是否为 JSON 数组格式（`["A", "B"]`），`published_at` 为空时必须设为 `NULL` 而非空字符串。
