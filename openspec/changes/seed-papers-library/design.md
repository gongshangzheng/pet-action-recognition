# Design: seed-papers-library

## Context

见 proposal.md - Why。当前状态：`data/papers.db` 为空；`data/extracted_papers.json` 有 140 篇博客提取论文；`scripts/import_papers.py` 已存在但**第一步清空整表**且用 `INSERT OR REPLACE`，重跑会覆盖 starred/pinned/note 等用户数据，不满足幂等要求。运行环境为本地 Mac（无 GPU 要求，纯网络 + SQLite 操作）。

## Goals / Non-Goals

**Goals:**
- 导入流程幂等：可重复执行，不丢用户数据（starred/pinned/note/blog_url）
- 两个方向（动作识别、动物动作/行为特征）的新论文入库并去重
- 核心论文标记可复核，清单文档与数据库标记一致

**Non-Goals:**
- 不改动论文模块前端/后端代码（列表、筛选、star API 已存在）
- 不做 LLM 自动分类/中文摘要生成（后续 change 再做）
- 不爬取 arXiv 全量检索；新论文以人工调研 + 定向检索的候选清单为准
- 不在远程服务器执行任何操作

## Decisions

### D1: 改造 import_papers.py 为幂等 upsert，而非另写新脚本

现有脚本已覆盖「读 JSON → arXiv 批量取元数据 → 写 SQLite」全链路，只需改写入策略：
- 删除「清空现有论文」步骤
- `INSERT OR REPLACE` → 先 `INSERT OR IGNORE`，再对已有记录仅 UPDATE 元数据字段（title/abstract/authors/published_at/pdf_url/external_ids/arxiv_categories/metadata），**不碰** starred/pinned/note/blog_url
- 备选方案：新建独立 upsert 脚本 —— 否决，避免两套导入逻辑漂移

### D2: 新论文调研产物落为 JSON 候选清单，复用同一导入管道

新调研论文整理成与 `extracted_papers.json` 同构的 JSON（如 `data/researched_papers.json`），import 脚本支持 `--input` 指定输入文件（默认仍为 extracted_papers.json）。这样存量/增量走同一条幂等管道，去重自然生效。
- 去重键：arXiv ID（规范化去版本号）优先；无 ID 时用标题归一化（小写、去标点）兜底
- 备选：直接手工 SQL 插入 —— 否决，不可重复、无元数据补全

### D3: 核心论文筛选与标记用独立脚本 + 清单数据文件

新增 `scripts/curate_core_papers.py`：读取一份人工维护的核心清单（JSON：arxiv_id/title → tier(core/pinned) + 入选理由），对库中匹配论文设置 starred=1 / pinned=1，并把入选理由写入 `note`（可复核性）。同一份清单 JSON 用于生成 Markdown 清单文档（`papers/docs/core-papers.md`），保证文档与数据库一致。
- 调研范围锚点（候选方向，最终以调研为准）：
  - 动作识别：Two-Stream、C3D、I3D、TSN、SlowFast、TimeSformer/ViViT/VideoMAE 系、X3D、MViT、Kinetics/Something-Something 数据集
  - 动物动作特征：DeepLabCut、SLEAP、AP-10K、APT-36K、Animal Kingdom、MammalNet、AnimalWeb、动物行为识别（MARS/BentoML 类）等
- 备选：直接在 DB 里手工 UPDATE 标记 —— 否决，不可复核、文档易漂移

### D4: arXiv API 限速与失败降级

批量请求保持现有 50/批 + sleep 节流；单批失败重试 2 次后跳过并记录，条目以 `manual` 来源、元数据字段 NULL（非空字符串）入库。

## Risks / Trade-offs

- [arXiv API 限流或网络失败导致部分元数据缺失] → 重试 + 降级入库，失败清单打印出来可二次补跑（幂等保证安全）
- [140 篇中部分 arxiv_id 格式脏（如 1504.01151 多一位）导致 API 查不到] → 导入时校验 ID 格式，非法 ID 走 manual 通道并记录
- [核心论文筛选带主观性] → 标准写死在 spec/清单 JSON 中，每篇附入选理由，用户可审核后调整
- [新旧来源重复（博客 140 篇与调研清单重叠）] → D2 去重键处理；重叠时保留已有记录的用户数据

## Migration Plan

纯数据变更，无 schema 迁移、无代码上线：
1. 备份 `data/papers.db`（虽为空库，保留习惯）
2. 改造并运行导入脚本（存量 140 篇）
3. 运行新论文导入（调研清单）
4. 运行核心标记脚本，生成清单文档
5. 回滚：`git checkout` 脚本改动 + 恢复 DB 备份即可
