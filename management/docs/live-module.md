---
title: Live 模块
author: 郑鑫裕
date: 2026-09-16
tags: [Live, 实时推理, SSE, 流媒体, 摄像头源, stream_token]
summary: Live 模块落地架构与关键决策——摄像头源管理、视频流代理、SSE 实时推理、截屏上传
id: 5
---

# Live 模块

> **怎么看**：§1 一句话定位 + 适用场景；§2 落地架构；§3 关键设计决策；§4 与 pet-videos 借鉴关系。详尽操作看 `.claude/skills/live/`。

## §1 定位与适用场景

**Live 模块**：连接一个或多个摄像头（或本地视频文件）→ 在浏览器里实时播放 → 同时调用 mmaction2 模型做**逐段动作推理**→ 把 top-k 结果实时回推给前端。

**适用场景**：在线调试模型、演示能力、临时观察某路摄像头的实时行为。**不是生产形态**——生产是抽查（详 [《系统架构》《系统架构》§4.6](../wiki/architecture)）。

## §2 落地架构

### §2.1 数据流（端到端）

```
[摄像头 / 视频文件]
       ↓ stream_url
[server/routers/live.py → 视频流代理（带 stream_token 签名）]
       ↓
[前端 VideoPlayer 组件（web/src/components/live/）]
       ↓ 用户点击"开始推理"
[SSE 连接 /api/live/inference/stream]
       ↓
[scripts/live_analyze.py / live_stream.py]
       ├─ decord 读帧（每帧一张）
       ├─ mmaction2 单帧→clip 滑动窗口 推理
       └─ 每 N 帧推一次 top-k 结果（同一个 SSE 通道）
       ↓
[前端 SSE 监听器 → 状态栏 + 进度条 + top-k 列表]
```

### §2.2 数据库（`server/db_live.py` + `results/live/live.db`）

- `stream_sources` 表：摄像头源（stream_url + storage_path + is_active）
- `screenshots` 表：截屏上传（前端拍图 → 后端存盘 → 关联到源）

### §2.3 stream_token 安全

视频流代理用 stream_token（短期签名）防止 URL 被盗链——前端拿 token 拼到 stream URL 里访问。

### §2.4 端点一览（`server/routers/live.py`）

| 端点 | 方法 | 用途 |
|---|---|---|
| `/api/live/sources` | GET / POST | 列出/创建摄像头源 |
| `/api/live/sources/{id}` | GET / PUT / DELETE | 单源 CRUD |
| `/api/live/sources/{id}/stream` | GET | 视频流代理（带 token） |
| `/api/live/screenshots` | POST | 上传截屏 |
| `/api/live/inference/stream` | GET (SSE) | 实时推理推送 |

## §3 关键设计决策

> 吸收自原 `live-page-integration-plan.md` + `live-realtime-inference-plan.md` 的决策节（两篇已删除，本节承接其落地现状）。计划体例（阶段拆分/执行顺序）已弃，不再保留。

### §3.1 真流式也要"切"，但切法不同

**问题**：mmaction2 输入是 clip（多帧短序列），不是单帧流；如何"实时"？

**答案**：滑动窗口——保持一个最近 N 帧的环形 buffer，每来新帧就推一次推理。看似"切"（clip 边界），实际无感（相邻 clip 重叠）。

```python
buffer = deque(maxlen=clip_len)
for frame in stream:
    buffer.append(frame)
    if len(buffer) == clip_len:
        clip = torch.stack([...buffer...])
        logits = model(clip)
        top_k = logits.topk(5)
        emit_sse(top_k)
```

### §3.2 模型选择 UI（t11-9）

前端 inference 启动面板里可下拉选模型（来自 [《模型》《模型》§5](../wiki/models) registry），运行时加载不同 mmaction2 checkpoint。注：实际生产环境通常预加载一个，避免每请求重新加载。

### §3.3 SSE vs WebSocket

选 **SSE（Server-Sent Events）**：单工（服务器推 → 客户端收），HTTP/1.1 友好，自动重连，适合"服务端不断推、客户端只收"。Live 模块不需要双向通信。

WebSocket 适合双向/低延迟场景——本模块不需要。

### §3.4 PTZ 摇杆 / 截屏上传

- PTZ：摄像头云台控制（云上/下/左/右/缩放），前端摇杆组件 → 后端代理到 ONVIF 或厂家私有协议
- 截屏：前端 Canvas 拍当前帧 → 上传 → 关联到 stream_source（用于后续人工标注）

## §4 与第三方借鉴

主要借鉴 **pet-videos**（详 [《第三方项目借鉴》](../wiki/third-party-notes)）：

- **借鉴**：多源切换 UI、视频播放器封装方式、截屏时序控制
- **未借鉴**：pet-videos 的"实时分类 + 多模型同时推理"导致 GPU 内存爆——本项目只跑单一模型

---

**相关文档**：`.claude/skills/live/`（操作指南）/ [《第三方项目借鉴》](../wiki/third-party-notes)（pet-videos 借鉴细节）/ [《系统架构》《系统架构》§4.6](../wiki/architecture)（Live 在管线中的角色）