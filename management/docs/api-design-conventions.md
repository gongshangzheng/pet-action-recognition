---
title: API 设计规范
author: 汤问
date: 2026-07-16
tags: [api, rest, 规范]
summary: 团队 REST API 设计的通用规范与最佳实践
---

## 基本原则

- 使用 RESTful 风格，资源命名用名词复数
- 统一返回 `{ data, error }` 结构
- 分页参数统一使用 `offset` + `limit`

## URL 规范

| 操作 | 方法 | 路径 |
|------|------|------|
| 列表 | GET | `/api/resource` |
| 详情 | GET | `/api/resource/{id}` |
| 创建 | POST | `/api/resource` |
| 更新 | PUT | `/api/resource/{id}` |
| 删除 | DELETE | `/api/resource/{id}` |

## 错误处理

所有错误返回统一格式：

```json
{
  "data": null,
  "error": {
    "code": 404,
    "message": "Resource not found"
  }
}
```

## 请求流程

```mermaid
sequenceDiagram
    participant C as 前端
    participant V as Vite Proxy
    participant F as FastAPI
    participant D as 数据层

    C->>V: GET /api/resource
    V->>F: 转发请求
    F->>D: 查询数据
    D-->>F: 返回结果
    F-->>V: { data, error }
    V-->>C: JSON 响应
```

## 系统架构

```mermaid
graph LR
    subgraph 前端
        Vue[Vue 3 SPA]
        Router[Vue Router]
        API[API Layer]
    end

    subgraph 后端
        FastAPI[FastAPI]
        Parsers[Parsers]
        DB[SQLite / Markdown]
    end

    Vue --> Router
    Vue --> API
    API -->|HTTP| FastAPI
    FastAPI --> Parsers
    Parsers --> DB
```

## 相关文档

- [[git-workflow|Git 工作流规范]] — 提交规范与分支策略
