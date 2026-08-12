---
name: web
description: |
  Web 全栈开发指南。用于前后端开发、服务启动、调试。
  触发场景：(1) 启动服务，(2) 开发前端页面，(3) 开发后端 API，(4) 调试，(5) 查看日志
---

# Web 全栈开发

本 skill 提供前后端开发的完整指南。

## 项目结构

```
pet-action-recognition/
├── server/                      # FastAPI 后端（:8788）
│   ├── main.py                 # 入口，注册 8 个 router
│   ├── config.py               # 配置（端口、CORS、路径常量）
│   ├── db.py                   # 论文 SQLite 操作
│   ├── db_live.py              # Live SQLite 操作
│   ├── live/                   # Live 安全模块
│   ├── routers/                # 8 个路由模块
│   │   ├── papers.py          # 论文路由
│   │   ├── management.py      # 项目管理路由（只读 Markdown）
│   │   ├── evaluation.py      # 评测路由
│   │   ├── training.py        # 训练路由
│   │   ├── speedrun.py        # Speed Run 路由
│   │   ├── datasets.py        # 数据集路由
│   │   └── live.py            # Live 路由
│   ├── parsers/               # Markdown 解析器
│   └── utils/                 # 工具函数
│
├── web/                        # Vue 3 前端（:3000）
│   ├── vite.config.js         # 代理 /api → 8788
│   └── src/
│       ├── api/              # API 请求封装
│       ├── layouts/          # MainLayout.vue
│       ├── router/index.js  # 路由配置
│       ├── views/           # 页面组件
│       ├── components/       # 通用组件
│       ├── stores/          # Pinia 状态管理
│       ├── styles/          # 全局样式
│       └── utils/           # 工具函数
│
├── management/                 # 项目管理数据（Markdown）
├── data/                      # papers.db, extracted_papers.json
└── results/                   # 训练/评测产物
```

## 启动服务

### 一键启动
```bash
bash start_services.sh
```

### 手动启动

**后端 (8788)**
```bash
cd ~/pet-action-recognition
lsof -i :8788 -sTCP:LISTEN  # 检查端口
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788
```

**前端 (3000)**
```bash
cd ~/pet-action-recognition/web
lsof -i :3000 -sTCP:LISTEN
npx vite --port 3000 --strict-port
```

访问 http://localhost:3000

## 后端路由

### 路由列表

| 模块 | 路由文件 | 前缀 | 用途 |
|------|----------|------|------|
| 论文 | `papers.py` | `/api/papers` | 论文 CRUD、笔记、收藏 |
| 管理 | `management.py` | `/api/management` | 团队、报表、任务、里程碑、会议、文档 |
| 评测 | `evaluation.py` | `/api/evaluation` | 模型、数据集、配置、结果 |
| 训练 | `training.py` | `/api/training` | 模型注册、训练 run、checkpoint |
| Speed Run | `speedrun.py` | `/api/speedrun` | 批量标注视频、结果流 |
| 数据集 | `datasets.py` | `/api/datasets` | 数据集管理 |
| Live | `live.py` | `/api/live` | 摄像头源、视频流、截屏、SSE 推理 |

### 主要 API 端点

```bash
# 论文
GET  /api/papers                    # 列表（分页/筛选）
GET  /api/papers/{id}               # 详情
GET  /api/papers/{id}/note          # 笔记
PUT  /api/papers/{id}/note          # 保存笔记
PUT  /api/papers/{id}/star          # 收藏
PUT  /api/papers/{id}/pin           # 置顶

# 管理（只读）
GET  /api/management/team           # 团队成员
GET  /api/management/daily          # 日报
GET  /api/management/weekly         # 周报
GET  /api/management/monthly        # 月报
GET  /api/management/tasks          # 任务看板
GET  /api/management/milestones     # 里程碑
GET  /api/management/meetings      # 会议纪要
GET  /api/management/projects       # 项目列表

# 训练
GET  /api/training/models           # 可训练模型
GET  /api/training/datasets        # 数据集
GET  /api/training/configs         # 训练配置
POST /api/training/run              # 触发训练
GET  /api/training/runs             # run 列表
GET  /api/training/run/{run_id}    # run 详情
POST /api/training/run_test         # 触发测试
GET  /api/training/test_results    # 测试结果
GET  /api/training/checkpoints      # checkpoint 列表
GET  /api/training/outputs/{path}   # 产物下载

# Speed Run
POST /api/speedrun/run             # 触发 speed run
GET  /api/speedrun/results          # 结果
GET  /api/speedrun/outputs/{path}  # 标注视频流

# Live
GET  /api/live/sources             # 摄像头源列表
POST /api/live/sources             # 添加源
PUT  /api/live/sources/{id}        # 更新源
DELETE /api/live/sources/{id}      # 删除源
GET  /api/live/play_url            # 获取播放 URL（带 stream_token）
GET  /api/live/stream              # 视频流代理
GET  /api/live/analyze/stream      # SSE 实时推理
GET  /api/live/screenshots         # 截屏列表
POST /api/live/screenshots         # 上传截屏

# 数据集
GET  /api/datasets                 # 数据集列表
GET  /api/datasets/{id}           # 数据集详情
```

## 前端开发

### 开发规范

- **框架**：Vue 3 + `<script setup>`
- **UI 库**：Naive UI
- **样式**：SCSS，组件内 `<style scoped>`
- **状态**：Pinia（stores/）
- **路由**：Vue Router

### 页面结构

```
web/src/views/
├── Home.vue                    # 首页
├── Live.vue                    # 实时视频流 + 推理
├── papers/
│   ├── PaperList.vue          # 论文列表
│   ├── PaperDetail.vue        # 论文详情
│   └── DataSource.vue         # 数据源配置
├── management/
│   ├── TeamList.vue           # 团队成员
│   ├── ReportPage.vue         # 报表（日报/周报/月报）
│   ├── TaskBoard.vue          # 任务看板
│   ├── MilestoneTimeline.vue  # 里程碑
│   ├── MeetingList.vue        # 会议纪要
│   ├── DocPage.vue            # Wiki 文档
│   └── Projects.vue           # 项目树
├── evaluation/
│   └── EvalResults.vue        # 评测结果
└── training/
    ├── SpeedRun.vue           # Speed Run
    ├── TrainConfigManage.vue  # 训练配置管理
    ├── TrainDatasetManage.vue # 训练数据集管理
    ├── TrainModelManage.vue   # 训练模型管理
    ├── TrainRun.vue           # 训练运行
    ├── TrainRunDetail.vue     # 训练运行详情
    └── TrainResults.vue       # 训练结果
```

### 组件结构

```
web/src/components/
├── common/                    # 通用组件
└── live/
    ├── VideoPlayer.vue        # 视频播放器
    ├── SourceManageModal.vue  # 摄像头源管理弹窗
    └── PtzJoystick.vue        # PTZ 控制摇杆
```

### API 请求封装

```javascript
// web/src/api/papers.js
import request from './request'

export function getPapers(params) {
  return request.get('/api/papers', { params })
}

export function getPaper(id) {
  return request.get(`/api/papers/${id}`)
}
```

### 创建新页面

1. 在 `web/src/views/` 创建 `.vue` 文件
2. 在 `web/src/router/index.js` 注册路由
3. 在侧边栏 `MainLayout.vue` 添加菜单项

## 调试

### 查看后端日志
```bash
tail -f /tmp/backend.log
```

### 测试 API
```bash
# 健康检查
curl http://localhost:8788/api/health

# 测试论文 API
curl http://localhost:8788/api/papers

# 测试 Live API
curl http://localhost:8788/api/live/sources
```

### 检查端口占用
```bash
lsof -i :8788   # 后端
lsof -i :3000   # 前端
```

### 前端调试
- Vue DevTools 浏览器扩展
- Network 面板查看 API 请求
- Console 查看错误信息

## 常用命令

```bash
# 重启后端
pkill -f "uvicorn server.main"
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788

# 重启前端
cd web && npm run dev

# 安装依赖
cd web && npm install

# 构建生产版本
cd web && npm run build
```

## 数据目录

| 模块 | 路径 |
|------|------|
| 论文 DB | `data/papers.db` |
| 论文原始 | `data/extracted_papers.json` |
| 训练产物 | `results/training/` |
| Speed Run | `results/speedrun/` |
| Live 数据 | `live/` |
| Checkpoints | `checkpoints/` |
| 团队成员 | `management/team/` |
| 报表 | `management/daily/weekly/monthly/` |
| 任务 | `management/projects/{slug}/tasks.json` |
