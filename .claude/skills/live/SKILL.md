---
name: live
description: |
  实时视频流 + 实时推理模块操作指南。用于摄像头源管理、视频流代理、SSE 推理、截屏上传。
  触发场景：(1) 添加/管理摄像头源，(2) 播放本地视频，(3) SSE 实时推理，(4) 截屏管理，(5) PTZ 控制
---

# Live 模块 — 实时视频流 + 实时推理

本 skill 提供 Live 模块的完整操作指南。

## 项目结构

```
server/
├── db_live.py              # SQLite 操作（摄像头源 + 截屏）
├── live/                   # 安全模块
│   └── security.py        # stream_token 编解码
└── routers/live.py        # API 路由

web/src/
├── views/Live.vue         # 主页面
└── components/live/
    ├── VideoPlayer.vue    # 视频播放器（带 overlay）
    ├── SourceManageModal.vue  # 源管理弹窗
    └── PtzJoystick.vue    # PTZ 摇杆

live/                      # 截屏存储（gitignore）
└── screenshots/         # 截屏图片

results/live/              # Live 推理产物（gitignore）
```

## 数据库结构

### stream_sources 表

```sql
CREATE TABLE stream_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- 源名称
    alias TEXT UNIQUE NOT NULL,  -- 别名（唯一）
    stream_url TEXT NOT NULL,     -- 视频流 URL
    storage_path TEXT NOT NULL,   -- 本地存储路径
    is_active INTEGER DEFAULT 1,   -- 是否启用
    created_at TEXT,              -- 创建时间
    updated_at TEXT               -- 更新时间
);
```

### screenshots 表

```sql
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,            -- 关联的摄像头源
    filename TEXT NOT NULL,       -- 文件名
    note TEXT,                    -- 备注
    created_at TEXT               -- 创建时间
);
```

## API 端点

### 摄像头源 CRUD

```bash
# 列出所有源
GET /api/live/sources

# 添加源
POST /api/live/sources
{
  "name": "客厅摄像头",
  "alias": "living-room",
  "stream_url": "/path/to/video.mp4",
  "storage_path": "/path/to/storage",
  "is_active": true
}

# 更新源
PUT /api/live/sources/{source_id}
{
  "name": "新名称",
  "stream_url": "/new/path.mp4",
  "is_active": false
}

# 删除源
DELETE /api/live/sources/{source_id}
```

### 视频文件

```bash
# 列出某源的视频文件
GET /api/live/sources/{source_id}/files

# 获取播放 URL（带 stream_token 签名）
GET /api/live/play_url?alias=living-room&filename=video.mp4

# 视频流代理（带 stream_token）
GET /api/live/stream?token=xxx
```

### 实时推理（SSE）

```bash
# SSE 实时推理
GET /api/live/analyze/stream?alias=xxx&filename=xxx&model_id=tsn-resnet50&model_type=mmaction2&clip_sec=1&stride_sec=2&device=cuda:0
```

SSE 事件格式：
```json
{"status": "loading_model", "model": "tsn-resnet50"}
{"status": "model_loaded", "model": "tsn-resnet50", "took_sec": 1.23}
{"t_start": 0.0, "t_end": 1.0, "label": "walk_dog", "score": 0.92, "top5": [...], "model": "tsn-resnet50"}
{"t_start": 1.0, "t_end": 2.0, "label": "running", "score": 0.88, "top5": [...], "model": "tsn-resnet50"}
{"status": "done", "total_segments": 10}
```

### 截屏管理

```bash
# 列出截屏
GET /api/live/screenshots
GET /api/live/screenshots?source_id=1   # 按源筛选

# 上传截屏
POST /api/live/screenshots
{
  "source_id": 1,
  "filename": "screenshot",
  "note": "异常行为",
  "data_url": "data:image/png;base64,xxxxx"
}
```

## 前端页面（Live.vue）

### 布局

```
┌─────────────┬──────────────────────┬─────────────┐
│  摄像头源   │      视频播放器       │  识别段    │
│  + 文件列表 │   + overlay 叠加     │   列表     │
│             │                      │             │
│  [源1]      │   ┌──────────────┐  │  walk_dog  │
│  [源2]      │   │   视频画面    │  │  92%      │
│  [源3]      │   │  + 预测叠加   │  │             │
│             │   └──────────────┘  │  running   │
│  [视频1]    │   GT: walk_dog      │  88%       │
│  [视频2]    │   pred: walk_dog    │             │
│             │                     │             │
│  ─────────  │   model: tsn-r50   │             │
│  推理控制   │                     │             │
│  [模型选择] │                     │             │
│  [设备选择] │                     │             │
│  [开始推理] │                     │             │
└─────────────┴──────────────────────┴─────────────┘
```

### 组件

| 组件 | 文件 | 用途 |
|------|------|------|
| 视频播放器 | `VideoPlayer.vue` | 播放视频 + overlay 叠加当前段的 top-1 预测 |
| 源管理弹窗 | `SourceManageModal.vue` | 添加/编辑摄像头源 |
| PTZ 摇杆 | `PtzJoystick.vue` | 云台控制（预留） |

### 推理控制

- **模型选择**：从训练模块加载可用模型
- **设备选择**：CPU / CUDA:0 / CUDA:1
- **步长控制**：推理的时间步长（秒）
- **开始/停止**：SSE 连接管理

## 安全机制

### stream_token

- 用于签名播放 URL，防止 URL 猜测
- 编码：`encode_stream_token(alias, filename)`
- 解码：`decode_stream_token(token)` → `(alias, filename)`
- 验证：`/api/live/play_url` 返回带 token 的 URL
- 流媒体服务：验证 token 后才提供服务

### safe_resolve

- 防止路径穿越攻击
- `storage_path` + `filename` → 验证结果在 `storage_path` 内

## 推理流程

### 1. 选择源 + 文件

1. 点击摄像头源 → 加载文件列表
2. 点击文件 → 调用 `/api/live/play_url` 获取带 token 的播放 URL

### 2. 开始推理

1. 选择模型 + 设备 + 步长
2. 点击"开始推理"
3. 建立 SSE 连接 `/api/live/analyze/stream`
4. 逐段接收推理结果

### 3. 播放 + 叠加

1. VideoPlayer 播放视频
2. 时间轴同步到当前段 → 显示 top-1 预测

## 截屏

### 前端截屏

- 点击播放器右上角"截图"按钮
- canvas → data URL → 下载到本地
- 同时上传到后端（关联当前源）

### 后端存储

- 保存到 `live/screenshots/` 或 `{storage_path}/screenshots/`
- 记录到 `screenshots` 表

## 常见问题

| 问题 | 解决 |
|------|------|
| 视频播放不了 | 确认是 H.264 编码；stream_token 是否有效 |
| SSE 连接中断 | 检查模型是否加载成功；设备是否可用 |
| 截屏上传失败 | 确认 `data_url` 格式正确（`data:image/png;base64,...`） |
| 推理结果为空 | 检查视频文件是否有效；模型是否正确 |

## 常用命令

```bash
# 查看摄像头源
curl http://localhost:8788/api/live/sources

# 获取播放 URL
curl "http://localhost:8788/api/live/play_url?alias=xxx&filename=xxx"

# 查看截屏
curl http://localhost:8788/api/live/screenshots

# 测试 SSE 推理
curl -N "http://localhost:8788/api/live/analyze/stream?alias=xxx&filename=xxx&model_id=tsn-resnet50&device=cpu"
```

## 与其他模块的关系

- **训练模块**：Live 使用训练好的模型进行推理
- **Speed Run**：Live 的单文件推理 vs Speed Run 的批量推理
- **评测模块**：评测结果可以在 Live 中可视化

详见：
- [[training]] — 模型训练
- [[testing]] — Speed Run
- [[evaluation]] — 评测模块
