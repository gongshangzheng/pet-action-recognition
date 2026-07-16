---
name: web
description: |
  Web 全栈开发指南。用于前后端开发、服务启动、调试等。
  触发场景：(1) 启动服务，(2) 开发前端页面，(3) 开发后端 API，(4) 调试，(5) 查看日志
---

# Web 全栈开发

本 skill 提供前后端开发的完整指南。

## 项目结构

```
<repo-root>/
├── server/              # FastAPI 后端
│   ├── config.py        # 配置
│   ├── main.py          # 入口
│   ├── db.py            # SQLite 操作
│   ├── routers/         # API 路由
│   │   ├── management.py
│   │   ├── papers.py
│   │   └── evaluation.py
│   └── parsers/        # Markdown 解析器
├── web/                 # Vue 3 前端
│   ├── src/
│   │   ├── api/        # API 请求
│   │   ├── views/      # 页面
│   │   └── router/     # 路由
│   └── vite.config.js
├── management/          # 项目管理数据
├── papers/              # 论文数据
├── evaluation/         # 评测数据
└── start_services.sh   # 启动脚本
```

## 启动服务

### 一键启动
```bash
cd <仓库根>
bash start_services.sh
```

### 手动启动

**后端 (8090)**
```bash
cd <仓库根>
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090
```

**前端 (3002)**
```bash
cd <仓库根>/web
npm run dev
```

访问 http://localhost:3002

## 后端开发

### API 端点

| 模块 | 端点 |
|------|------|
| 团队 | `/api/management/team` |
| 项目树 | `/api/management/projects` |
| 日报 | `/api/management/daily` |
| 周报 | `/api/management/weekly` |
| 月报 | `/api/management/monthly` |
| 任务 | `/api/management/tasks` |
| 里程碑 | `/api/management/milestones` |
| 会议 | `/api/management/meetings` |
| 论文 | `/api/papers` |
| 评测 | `/api/evaluation/*` |

### 调试后端

```bash
# 查看日志
tail -f /tmp/backend.log

# 测试 API
curl http://localhost:8090/api/management/team
```

## 前端开发

### 开发规范

- 框架：Vue 3 + `<script setup>`
- UI：Naive UI
- 样式：SCSS `<style scoped>`

### 创建页面

1. 在 `web/src/views/` 创建 `.vue` 文件
2. 在 `web/src/router/index.js` 注册路由

### 常用组件

```vue
<template>
  <n-button type="primary">按钮</n-button>
  <n-input v-model:value="text" />
  <n-card title="卡片">内容</n-card>
  <n-table :columns="columns" :data="data"></n-table>
</template>

<script setup>
import { NButton, NInput, NCard, NTable } from 'naive-ui'
</script>
```

## 数据目录

| 模块 | 路径 |
|------|------|
| 团队成员 | `management/team/` |
| 日报 | `management/daily/YYYY/MM/` |
| 周报 | `management/weekly/YYYY/` |
| 月报 | `management/monthly/YYYY/` |
| 任务 | `management/docs/projects/{slug}/tasks.json`（看板+项目树单源） |
| 里程碑 | `management/docs/milestones.md` |
| 会议 | `management/docs/meetings/` |
| 论文 | `data/papers.db` |
| 模型 | `evaluation/models/` |
| 数据集 | `evaluation/datasets/` |
| 评测结果 | `evaluation/results/` |

## 常用命令

```bash
# 重启后端
pkill -f "uvicorn server.main"
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090

# 重启前端
cd web && npm run dev

# 查看端口
lsof -i :8090  # 后端
lsof -i :3002  # 前端
```
