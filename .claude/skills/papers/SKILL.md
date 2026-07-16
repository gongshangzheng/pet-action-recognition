---
name: papers
description: |
  论文搜集模块操作指南。用于论文导入、分类、笔记管理、搜索筛选等操作。
  触发场景：(1) 导入新论文，(2) 管理论文分类，(3) 添加/查看论文笔记，(4) 搜索筛选论文
---

# 论文搜集模块

本 skill 提供论文搜集模块的完整操作指南。

## 项目结构

```
papers/
├── config/         # 数据源配置
├── data/          # 论文数据（SQLite）
├── cache/          # 缓存
└── scripts/        # 导入脚本

data/
└── papers.db       # SQLite 数据库
```

## 启动服务

```bash
# 后端 (8090)
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090
```

---

## 1. 论文数据库

### 表结构

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,          -- 论文 ID (arXiv ID)
    title TEXT,                   -- 标题
    authors TEXT,                 -- 作者
    abstract TEXT,                -- 摘要
    source TEXT,                 -- 来源 (arxiv, custom 等)
    category TEXT,               -- 分类
    published_date TEXT,         -- 发布日期
    starred INTEGER,             -- 收藏 0/1
    pinned INTEGER,              -- 置顶 0/1
    note TEXT,                   -- 笔记
    blog_url TEXT,               -- 博客链接
    created_at TEXT,             -- 创建时间
    updated_at TEXT              -- 更新时间
);
```

### API 端点

```bash
# 获取论文列表（分页、筛选）
GET /api/papers?limit=100&offset=0&source=arxiv&category=LLM

# 获取论文统计
GET /api/papers/stats/summary

# 获取论文详情
GET /api/papers/{paper_id}

# 获取论文笔记
GET /api/papers/{paper_id}/note

# 保存论文笔记
PUT /api/papers/{paper_id}/note
Content-Type: application/json
{"content": "笔记内容"}

# 收藏/取消收藏
PUT /api/papers/{paper_id}/star
Content-Type: application/json
{"starred": true}

# 置顶/取消置顶
PUT /api/papers/{paper_id}/pin
Content-Type: application/json
{"pinned": true}

# 设置博客链接
PUT /api/papers/{paper_id}/blog
Content-Type: application/json
{"blog_url": "https://blog.example.com/paper"}
```

---

## 2. 导入论文

### 导入 JSON 格式

创建 JSON 文件，格式如下：

```json
[
  {
    "id": "2301.12345",
    "title": "Paper Title",
    "authors": "Author One, Author Two",
    "abstract": "Paper abstract...",
    "source": "arxiv",
    "category": "LLM",
    "published_date": "2023-01-15"
  }
]
```

然后通过 API 导入：

```bash
# 查找导入接口或直接操作数据库
python3 -c "
import sqlite3
import json

with open('papers.json') as f:
    papers = json.load(f)

conn = sqlite3.connect('data/papers.db')
cursor = conn.cursor()

for p in papers:
    cursor.execute('''
        INSERT OR REPLACE INTO papers 
        (id, title, authors, abstract, source, category, published_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (p['id'], p['title'], p['authors'], p['abstract'], 
          p.get('source', 'custom'), p.get('category', ''), 
          p.get('published_date', '')))

conn.commit()
conn.close()
print(f'Imported {len(papers)} papers')
"
```

### 数据源配置

在 `papers/config/` 目录下添加数据源配置：

```yaml
# papers/config/arxiv.yaml
source: arxiv
categories:
  - cs.CL
  - cs.AI
keywords:
  - "language model"
  - "transformer"
```

---

## 3. 论文分类管理

### 分类方式

1. **按来源**: arxiv, custom, blog
2. **按领域**: LLM, CV, NLP, RL, etc.

### 修改论文分类

```bash
# 直接操作数据库
sqlite3 data/papers.db "UPDATE papers SET category = 'LLM' WHERE id = '2301.12345'"
```

### 批量更新分类

```bash
# 按关键词批量分类
sqlite3 data/papers.db "
UPDATE papers SET category = 'LLM' 
WHERE title LIKE '%language model%' OR title LIKE '%LLM%' OR abstract LIKE '%language model%';
"
```

---

## 4. 论文笔记

### 保存笔记

```bash
# API 方式
curl -X PUT http://localhost:8090/api/papers/2301.12345/note \
  -H "Content-Type: application/json" \
  -d 'content=这是我的笔记内容...'

# 直接数据库
sqlite3 data/papers.db "
UPDATE papers SET note = '笔记内容', updated_at = datetime('now') 
WHERE id = '2301.12345';
"
```

### 查看笔记

```bash
GET /api/papers/{paper_id}/note
# 或
GET /api/papers/{paper_id}  # 返回包含 note 字段
```

---

## 5. 常用查询

### 统计论文数量

```bash
sqlite3 data/papers.db "SELECT source, COUNT(*) FROM papers GROUP BY source;"

# 按分类统计
sqlite3 data/papers.db "SELECT category, COUNT(*) FROM papers WHERE category != '' GROUP BY category;"
```

### 搜索论文

```bash
# 标题搜索
sqlite3 data/papers.db "SELECT * FROM papers WHERE title LIKE '%keyword%' LIMIT 10;"

# 作者搜索
sqlite3 data/papers.db "SELECT * FROM papers WHERE authors LIKE '%author%';"

# 已收藏论文
sqlite3 data/papers.db "SELECT * FROM papers WHERE starred = 1;"
```

### 置顶论文

```bash
# 置顶
sqlite3 data/papers.db "UPDATE papers SET pinned = 1 WHERE id = '2301.12345';"

# 取消置顶
sqlite3 data/papers.db "UPDATE papers SET pinned = 0 WHERE id = '2301.12345';"
```

---

## 6. 数据导出

### 导出为 JSON

```bash
sqlite3 -json data/papers.db "SELECT * FROM papers;" > papers_export.json
```

### 导出为 CSV

```bash
sqlite3 -csv data/papers.db "SELECT id, title, authors, category FROM papers;" > papers.csv
```
