# Mermaid 语法速查

本文档是 `docs` skill 的参考文件，供在 ProjFlow 的 Wiki/会议/报告文档中绘制 Mermaid 图表时查阅。

## 1. 通用规则

- 每个 Mermaid 块以 ` ```mermaid ` 开始，以 ` ``` ` 结束。
- Mermaid 不支持中文节点名中混有特殊符号时可能渲染失败，尽量用英文标识或简短中文。
- 节点文本过长时，用 `A["长文本"]` 包裹双引号。
- 复杂图表建议拆成多个小图，不要一个图塞 20+ 节点。

## 2. 流程图（flowchart）

### 2.1 方向

- `flowchart TD` — 自上而下（Top Down）
- `flowchart LR` — 从左到右（Left Right）
- `flowchart BT` — 自下而上
- `flowchart RL` — 从右到左

### 2.2 节点形状

```mermaid
flowchart LR
    A[矩形] --> B(圆角矩形)
    B --> C{菱形判断}
    C -->|是| D[/平行四边形/]
    C -->|否| E((圆形))
    D --> F>旗形]
```

语法对照：

| 形状 | 语法 | 用途 |
|------|------|------|
| 矩形 | `A[文本]` | 普通步骤 |
| 圆角矩形 | `A(文本)` | 开始/结束 |
| 菱形 | `A{文本}` | 判断/分支 |
| 圆形 | `A((文本))` | 关键节点 |
| 平行四边形 | `A[/文本/]` | 输入/输出 |
| 旗形 | `A>文本]` | 结果/终点 |

### 2.3 连线与标签

```mermaid
flowchart TD
    A --> B        %% 无标签实线
    A -->|标签| C  %% 带标签实线
    B -.-> D       %% 虚线
    C ==> E        %% 粗线
    D -- 说明 --> E
```

### 2.4 子图

```mermaid
flowchart TB
    subgraph 前端
        V1[Vue 3]
        V2[Vue Router]
    end

    subgraph 后端
        F1[FastAPI]
        F2[Parsers]
    end

    V1 --> V2
    V1 -->|API 调用| F1
    F1 --> F2
```

## 3. 时序图（sequenceDiagram）

```mermaid
sequenceDiagram
    participant C as 客户端
    participant P as Vite Proxy
    participant S as FastAPI
    participant D as SQLite

    C->>P: GET /api/resource
    P->>S: 转发请求
    activate S
    S->>D: SELECT * FROM table
    D-->>S: 返回结果
    deactivate S
    S-->>P: { data, error }
    P-->>C: JSON 响应
```

常用语法：

| 语法 | 含义 |
|------|------|
| `participant A as 显示名` | 定义参与者别名 |
| `A->>B: 消息` | 实心箭头（同步调用） |
| `A-->>B: 消息` | 虚线箭头（返回） |
| `A->>B+` / `A-->>B-` | 激活/取消激活生命线 |
| `Note over A,B: 备注` | 跨参与者备注 |
| `loop 条件` ... `end` | 循环 |
| `alt 条件` ... `else` ... `end` | 条件分支 |

## 4. 架构图（graph）

`graph` 与 `flowchart` 基本等价，旧文档中常见。

```mermaid
graph LR
    subgraph 前端层
        A[Vue 3 SPA]
        B[API Layer]
    end

    subgraph 服务层
        C[FastAPI]
        D[Router]
    end

    subgraph 数据层
        E[(SQLite)]
        F[(Markdown)]
    end

    A --> B
    B -->|HTTP/JSON| C
    C --> D
    D --> E
    D --> F
```

## 5. 甘特图（gantt）

```mermaid
gantt
    title 7 月开发排期
    dateFormat  YYYY-MM-DD
    section 架构
    后端脚手架       :done, a1, 2026-07-01, 7d
    前端脚手架       :done, a2, 2026-07-01, 7d
    section UI 改造
    报告页合并       :done, b1, 2026-07-10, 5d
    文档 Wiki 布局   :done, b2, 2026-07-14, 4d
    section 待办
    评测 UI 优化     :c1, 2026-08-01, 7d
```

常用语法：

| 语法 | 含义 |
|------|------|
| `section 名称` | 分组 |
| `:done, id, 日期, 时长` | 已完成任务 |
| `:active, id, 日期, 时长` | 进行中任务 |
| `:id, 日期, 时长` | 未开始任务 |
| `:crit, id, 日期, 时长` | 关键任务（红色高亮） |
| `:after id` | 依赖前置任务 |

## 6. 类图（classDiagram）

适用于数据模型/组件关系说明。

```mermaid
classDiagram
    class Task {
        +String id
        +String title
        +String status
        +String assignee
        +Progress[] progress
        +addProgress(note)
    }

    class Progress {
        +String date
        +String note
    }

    Task "1" --> "*" Progress : has
```

## 7. 项目常用图例

### 7.1 请求链路

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as /api/management/docs
    participant Router as management.py
    participant Parser as report_parser
    participant File as management/docs/*.md

    FE->>API: GET /docs/api-design-conventions
    API->>Router: 路由分发
    Router->>Parser: 解析 frontmatter + body
    Parser->>File: 读取文件
    File-->>Parser: markdown 内容
    Parser-->>Router: { slug, title, content }
    Router-->>API: JSON
    API-->>FE: 渲染详情页
```

### 7.2 任务状态流转

```mermaid
flowchart LR
    planned --> active
    active --> completed
    active --> paused
    active --> blocked
    paused --> active
    blocked --> active
    completed --> active
```

### 7.3 项目树数据流

```mermaid
flowchart TD
    A[management/projects/{slug}/tasks.json] -->|递归展平| B[tasks_parser]
    B -->|按 status 分桶| C[看板]
    B -->|层级渲染| D[项目树]
    C --> E[completed]
    C --> F[in_progress]
    C --> G[pending]
```

## 8. 调试技巧

- Mermaid 渲染失败时，常见原因：
  1. 节点文本含未转义的特殊字符（如 `(`、`)`、`[`、`]`、`{`、`}`）。
  2. 同一图表中节点 ID 重复。
  3. 连线语法错误（如 `A --> B` 写成 `A -> B` 在部分语法中不合法）。
- 在线验证：https://mermaid.live/
