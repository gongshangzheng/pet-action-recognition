---
name: papers
description: |
  论文搜集模块操作指南。用于论文导入、分类、笔记管理、搜索筛选、数据源配置。
  触发场景：(1) 导入新论文，(2) 管理论文分类，(3) 添加/查看论文笔记，(4) 搜索筛选论文，(5) 配置数据源
---

# 论文搜集模块

本 skill 提供论文搜集模块的完整操作指南。

## 项目结构

```
papers/                        # 论文模块（空壳目录，真实数据在 data/）
├── config/                    # 数据源配置
├── docs/                     # 文档
└── scripts/                  # 脚本

data/
├── extracted_papers.json      # 从博客提取的原始数据（140 篇）
└── papers.db                 # SQLite 数据库（论文元数据 + 笔记）
```

## 启动服务

```bash
bash start_services.sh
# 或手动
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788
```

---

## 1. 数据库结构

### papers 表

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,              -- arXiv ID 或其他来源 ID
    title TEXT,                        -- 英文标题
    title_zh TEXT,                     -- 中文标题（可选）
    abstract TEXT,                     -- 英文摘要
    abstract_zh TEXT,                  -- 中文摘要（可选）
    authors TEXT,                      -- JSON 数组字符串，如 '["Author A", "Author B"]'
    published_at TEXT,                  -- 发布日期 (ISO 8601)
    crawled_at TEXT,                    -- 抓取时间
    url TEXT,                          -- 论文 URL
    pdf_url TEXT,                      -- PDF URL
    source TEXT,                       -- 来源：arxiv / blog / manual
    external_ids TEXT,                  -- JSON：{arxiv: "xxx", doi: "xxx"}
    summary_zh TEXT,                    -- LLM 生成的中文摘要
    relevance_score REAL,              -- 相关性评分（0-1）
    llm_classification TEXT,           -- JSON：LLM 分类结果
    metadata TEXT,                      -- JSON：其他元数据
    arxiv_categories TEXT,              -- JSON：arXiv 分类列表
    starred INTEGER DEFAULT 0,          -- 收藏（0/1）
    pinned INTEGER DEFAULT 0,          -- 置顶（0/1）
    blog_url TEXT,                      -- 关联的博客链接
    note TEXT                           -- 个人笔记
);
```

**重要**：`authors` 是 JSON 数组字符串，不是普通逗号分隔的字符串。解析时需要 `json.loads()`。

### paper_categories 表

```sql
CREATE TABLE paper_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT,
    category TEXT,
    confidence REAL,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);
```

---

## 2. API 端点

### 论文列表

```bash
GET /api/papers
# Query 参数：
#   limit=20        # 每页数量
#   offset=0        # 偏移
#   search=keyword  # 搜索标题/摘要
#   source=arxiv    # 按来源筛选
#   starred=true    # 只看收藏
#   pinned=true     # 只看置顶
#   sort=published_at_desc  # 排序方式
```

### 论文详情

```bash
GET /api/papers/{paper_id}
```

### 论文笔记

```bash
# 获取笔记
GET /api/papers/{paper_id}/note

# 保存笔记
PUT /api/papers/{paper_id}/note
Content-Type: application/json
{"content": "笔记内容..."}
```

### 收藏/置顶

```bash
# 收藏
PUT /api/papers/{paper_id}/star
{"starred": true}

# 置顶
PUT /api/papers/{paper_id}/pin
{"pinned": true}
```

### 博客链接

```bash
PUT /api/papers/{paper_id}/blog
{"blog_url": "https://blog.example.com/paper"}
```

### 统计

```bash
GET /api/papers/stats/summary
```

---

## 3. 导入论文

### 从 arXiv 导入

```bash
python scripts/import_papers.py
```

脚本会：
1. 从博客 `~/gongshangzheng.github.io/src/pages/` 提取论文信息
2. 保存到 `data/extracted_papers.json`
3. 从 arXiv API 获取元数据
4. 写入 `data/papers.db`

### 导出论文

```bash
python scripts/export_papers.py --output exported.json
```

---

## 4. 论文分类管理

### 分类方式

1. **LLM 自动分类**：`llm_classification` 字段（JSON）
2. **手动分类**：通过 API 或直接操作数据库
3. **arXiv 分类**：`arxiv_categories` 字段

### 批量更新分类

```bash
sqlite3 data/papers.db "
UPDATE papers SET starred = 1 WHERE title LIKE '%action recognition%';
"
```

---

## 5. 论文笔记

### 保存笔记

```bash
curl -X PUT http://localhost:8788/api/papers/2301.12345/note \
  -H "Content-Type: application/json" \
  -d '{"content": "这是我的笔记内容..."}'
```

### 笔记字段

笔记保存在 `papers.note` 字段，支持自由格式文本。

---

## 6. 搜索筛选

### 前端筛选

- **搜索框**：搜索标题、摘要
- **时间下拉**：按发布日期筛选
- **分类下拉**：按 arXiv 分类筛选
- **收藏开关**：只看收藏论文
- **排序**：按发布时间、相关性、收藏时间

### SQL 查询示例

```bash
# 搜索标题
sqlite3 -json data/papers.db "SELECT * FROM papers WHERE title LIKE '%transformer%' LIMIT 10;"

# 按来源统计
sqlite3 data/papers.db "SELECT source, COUNT(*) FROM papers GROUP BY source;"

# 收藏论文
sqlite3 -json data/papers.db "SELECT * FROM papers WHERE starred = 1;"

# 置顶论文（置顶优先显示）
sqlite3 -json data/papers.db "SELECT * FROM papers WHERE pinned = 1 ORDER BY starred DESC;"

# 按 arXiv 分类筛选
sqlite3 -json data/papers.db "
SELECT * FROM papers WHERE arxiv_categories LIKE '%cs.CV%';
"
```

---

## 7. 数据源配置

### 博客数据源

论文来源于博客 `~/gongshangzheng.github.io` 中「AI/动作识别」分类。

### JSON 格式

`data/extracted_papers.json` 格式：

```json
[
  {
    "id": "2301.12345",
    "title": "Paper Title",
    "authors": ["Author One", "Author Two"],
    "abstract": "Paper abstract...",
    "source": "arxiv",
    "published_at": "2023-01-15",
    "url": "https://arxiv.org/abs/2301.12345",
    "blog_url": "https://blog.example.com/paper"
  }
]
```

---

## 8. 常用命令

```bash
# 查看论文数量
sqlite3 data/papers.db "SELECT COUNT(*) FROM papers;"

# 查看收藏数量
sqlite3 data/papers.db "SELECT COUNT(*) FROM papers WHERE starred = 1;"

# 导出为 CSV
sqlite3 -csv data/papers.db "SELECT id, title, authors, source FROM papers;" > papers.csv

# 清空笔记
sqlite3 data/papers.db "UPDATE papers SET note = NULL WHERE 1=1;"

# 重置收藏/置顶
sqlite3 data/papers.db "UPDATE papers SET starred = 0, pinned = 0 WHERE 1=1;"
```

---

## 9. 注意事项

1. **`authors` 字段是 JSON**：解析时必须 `json.loads()`，不要直接当字符串处理
2. **`published_at` 为空**：必须设为 `NULL`，不能是空字符串
3. **`arxiv_categories` 是 JSON 数组**：包含该论文的所有 arXiv 分类
4. **置顶论文优先显示**：列表中置顶论文始终在最前
5. **笔记保存在 `note` 字段**：不是单独的表

---

## 10. 与其他模块的关系

- **训练模块** 可以引用论文作为参考
- **评测模块** 可能需要论文中的方法作为 baseline
- **项目管理** 可以关联论文到任务

详见：
- [[training]] — 训练模块
- [[evaluation]] — 评测模块
- [[management]] — 项目管理
