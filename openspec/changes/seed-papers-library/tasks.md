# Tasks: seed-papers-library

## 0. 论文收录模块健康检查与修复

> 检查结论：DB schema 正常、后端 API 正常、extracted_papers.json 140 篇（97 有 arXiv ID、43 无、无重复 ID）。以下问题需先修复：

- [x] 0.1 修复 `scripts/import_papers.py` manual ID 不稳定 bug：`hash(title)` 跨进程随机，改用稳定哈希（如 sha1(title) 前 12 位），否则 43 篇 manual 论文重跑必产生重复
- [x] 0.2 修复清表 + `INSERT OR REPLACE`：改为幂等 upsert，重跑不丢 starred/pinned/note/blog_url
- [x] 0.3 修复 arXiv 元数据缺失条目被 SKIP 丢弃：降级为 manual 来源入库并记录警告清单
- [x] 0.4 增加 `--input` 参数（默认 `data/extracted_papers.json`）与 arXiv API 失败重试（2 次后降级跳过）
- [x] 0.6 实施中发现的补充修复：后端 `/api/papers` 未实现 spec 要求的 `search/starred/pinned` 过滤（空库时不可见），已在 `server/db.py::query_papers` + `server/routers/papers.py::list_papers` 补齐并验证
- [x] 0.5 冒烟验证：导入两次，总数一致、无重复 ID（`SELECT id, COUNT(*) FROM papers GROUP BY id HAVING COUNT(*)>1` 为空）

## 1. 存量论文导入

- [x] 1.1 备份 `data/papers.db`（如已存在数据）
- [x] 1.2 运行存量导入：`python3 scripts/import_papers.py`，确认 140 篇入库（含 43 篇 manual 通道）
- [x] 1.3 幂等验证：重跑一次导入，确认总数不变、无重复、无 manual ID 漂移

## 2. 新论文调研与收录

> 调研已完成两轮并全部经 arXiv API 核验：第一轮 3 个 researcher 专题（77 条候选，凭训练知识）；第二轮真实 API 检索（arXiv 搜索 + Semantic Scholar 尝试）补充发现 ~30 篇新工作；两轮所有 ID 经 `export.arxiv.org` 批量核验，**修正 19 个错误 ID、裁决 2 个冲突、剔除 1 个不存在的论文（PoseBridge）**。最终清单见本 change 目录 `research-verified.json`（含 verified/manual 通道标记）。

- [x] 2.1 从 `research-verified.json` 生成 `data/researched_papers.json`（与 extracted_papers.json 同构）：verified 条目带 arxiv_id 走 arXiv 通道；manual 条目（DeepLabCut/SLEAP/JAABA/MoSeq/MARS/B-SOiD/A-SOiD/DeepEthogram/LabGym/DANNCE/Anipose/VAME/Keypoint-MoSeq 等 Nature/eLife 系）带 URL/DOI 走 manual 通道
- [x] 2.2 与存量 140 篇预去重（Two-Stream/SlowFast/VideoMAE/Animal Kingdom 等可能已在博客清单中）
- [x] 2.3 运行增量导入：`python3 scripts/import_papers.py --input data/researched_papers.json`，确认零 MISS（有 MISS 则人工核查该条目）
- [x] 2.4 验证四方向覆盖：SQL 检索确认前沿方法、动物姿态/行为、few-shot、迁移四类文献均在库（含 2025–2026 最新作，如 Promptable Animal Pose Tracking、动物动作识别综述）

## 3. 核心论文标记与清单

- [x] 3.1 按 spec 标准筛选核心论文，产出核心清单 JSON（arxiv_id/title → tier: core/pinned + 入选理由）。锚点（用户点名必收）：Two-Stream (1406.2199)、I3D、SlowFast (1812.03982)、VideoMAE (2203.12602)、DeepLabCut、Animal Kingdom (2204.08129)；调研推荐的追加候选：VideoMAE V2、InternVideo2、VideoPrism、AIM（参数高效，适合小数据）、SuperAnimal（四足零样本姿态）、APT-36K/AP-10K、MammalNet、Keypoint-MoSeq、OTAM/TRX（few-shot 代表）
- [x] 3.2 新增 `scripts/curate_core_papers.py`：读取清单 JSON，设置 starred=1 / pinned=1，将入选理由写入 note
- [x] 3.3 运行标记脚本，验证 `GET /api/papers?starred=true` / `?pinned=true` 返回结果（或直接 SQL 验证）
- [x] 3.4 生成 `papers/docs/core-papers.md` 中文清单（按主题分组：标题、年份/出处、一句话价值、链接、入选理由），与数据库标记核对一致；附专题 C 的路线综合判断（迁移优先、自监督续训、姿态桥接辅助）作为选型指南

- [ ] 2.5 （遗留）arXiv 解禁后重跑 `python3 scripts/import_papers.py --input data/researched_papers.json` 与默认导入，升级作者/精确日期/arXiv 分类（幂等 upsert，安全）

## 5. 前沿调研总结文档

> 用户需求：搞清动作识别与宠物动作方向的最前沿论文、主要技术路线、以及当前库可借鉴的结论，总结成一篇文档。

- [x] 5.1 撰写 `papers/docs/research-landscape.md`（中文）：① 领域地图（动作识别六条技术路线 + 动物动作三条路线）② 各路线代表论文（引用已核验的 arXiv ID）③ 两大核心问题的证据链 ④ 对本项目的可落地借鉴结论（训练/评测/live/VLM 四个维度）⑤ 与数据库/核心清单的交叉引用
- [ ] 5.2 提交文档（docs: 前缀）

## 4. 收尾

- [x] 4.1 启动后端，前端论文列表页人工抽查（置顶优先、搜索可用）
- [x] 4.2 向用户汇报核心论文清单摘要
- [x] 4.3 提交变更（脚本 + 清单 JSON + 文档；不提交 papers.db 等 gitignore 产物）
