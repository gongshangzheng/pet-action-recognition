# AGENTS.md — 宠物动作识别研究平台

> 本文件供 AI Agent 阅读，用于理解项目架构、开发规范和工作流程。

## 当前交付目标与排程

- 完成闭集行为识别训练：准确率 75% 以上、漏检率 10% 以下。准确率的统计单位与汇总方式、漏检的匹配规则及分母须在评测协议中审定；不得把门控召回或片段分类成绩冒充端到端成绩。
- **中期目标（2026-11-07 记录；口径 2026-11-07 用户裁定修订）**：闭集行为识别达到准确率 ≥75%、漏检率 ≤10%。
  - **准确率口径（用户裁定）**：在留出的验证/测试子集上判对的比例（条件准确率）。当前划分为 train 60% / val 25% / test 15%，达标判定以测试集为准；当前测试集 top-1 为 85.75%，**已达 75% 目标**。
  - 端到端口径（可用率 × 条件准确率，分母为全部 3,927 条标注，失败计错）作为诊断量同时披露，当前 72.9%，不作为达标判定。
  - 漏检率须先定义单位再上报：区间级取 `1 − recall`，当前测试集为 14.25%（逐类最高 scratching 43.6%、drinking 31.7%），**未达 10% 目标**；事件级需要动作定位与匹配规则，当前尚无定位能力。
  - 当前基线（2026-11-07）：可用区间 3,339 / 3,927 = 85%（旧数据集为 207 / 2,710 = 7.6%）。按轨迹裁剪后训练十类 VideoMAEv2-B，测试集 1,130 条片段的 top-1 为 **85.75%**（≥75% 目标达成）、macro-F1 56.23%；端到端诊断量 85.03% × 85.75% ≈ 72.9%；区间级漏检率 14.25%（逐类最高 scratching 43.6%、drinking 31.7%），漏检目标未达成。整帧对照臂只跑了 4 轮（验证 top-1 75.95%），不能与 20 轮直接比较。
- 完成开发板端侧与云端系统集成：宠物行为上报、统计、视频流直播、跟拍、设备控制、视频回放、亮点抓取。
- 提取画面亮度、对比度、宠物活动幅度、身体在画面中的面积占比及持续时长、面部暴露面积占比及持续时长，以及行为识别信息，并上报云端判断。面积分母、有效观测与累计时长规则需明确，不擅自确定。
- 当前主线是存在性检测、宠物定位、动作分割、闭集行为识别、空间状态与观测指标、端云集成及联合验收。
- identity-action-tokenizer 的身份向量与动作向量研究、video-feature-latent 的行为发现与聚类研究均搁置，当前完全不推进，也不作为动作分割、闭集分类或产品集成的前置。
- 背景移除及新增 SORT 等关联器为 optional，整体管线跑通后再研究收益。多猫关联未验证时，必须明确其限制。
- 架构文档及计划用组件全名，例如存在性检测、动作分割、背景移除，不使用 L1、L2 等层号作为组件名称。标题简洁明了。
- 回复按组件组织，给出该组件的目的、输入输出、已知事实及证据边界、待办和依赖；遵守格赖斯准则，不夸大完成度、不遗漏影响判断的信息，不堆砌无关细节。

## 设计讨论方式

存在性检测统一由 `presence-gate-model` 管理，模型输入仅RGB。视频架构独立选型，用户已确认X3D-XS，不受图像骨干约束。按用户要求先标图片并训练初评，再标视频并训练初评，首轮每阶段仅几百样本。保留独立像素变化调度，禁止以低运动直接判无宠物。

设计细节必须先与用户讨论，由用户决定。先讲解组件全景、输入输出和关系，确认用户理解后再逐步深入；候选、建议与已定决定明确区分，未讨论的细节不得写成强制要求。当前优先讨论并确定存在性检测、动作分割和空间状态；动作分割先研究现有模型，提出有来源、条件和限制的可行方案，再由用户选择。

## 项目概述

宠物动作识别研究平台，用于管理动作识别相关论文、团队协作、模型训练和实时推理。

论文数据来源于博客仓库 `~/gongshangzheng.github.io` 中「AI/动作识别」分类下的 17 篇文章，从中提取了 140 篇相关论文。

## 技术栈

| 层 | 技术 | 端口 |
|----|------|------|
| 前端 | Vue 3 + Vite + Naive UI + Vue Router | 3000 |
| 后端 | FastAPI (Python) | 8788 |
| 数据库 | SQLite (data/papers.db) + JSON 文件 | — |

### 服务架构

```
浏览器 → Vite (3000) → FastAPI (8788) → SQLite (data/papers.db)
                   ↘ FastAPI → management/ (Markdown 文件)
                   ↘ FastAPI → live/ (视频流 + 截屏数据库)
                   ↘ FastAPI → results/ (训练/评测产物)
```

- **前端**：Vue 3 SPA，通过 Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，直接操作 SQLite 数据库，读写 `management/` 下的 Markdown 文件
- **Live 模块**：摄像头源管理、视频流代理、实时推理（SSE）
- **数据库**：本地 SQLite + JSON 文件，独立于任何外部服务

## 启动服务

```bash
# 一键启动（后端 8788 + 前端 3000）
bash start_services.sh

# 或手动启动：
# 1. 后端
cd ~/pet-action-recognition
nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788 </dev/null > /tmp/backend.log 2>&1 & disown

# 2. 前端
cd ~/pet-action-recognition/web
nohup npx vite --port 3000 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
```

## 目录结构

```
pet-action-recognition/
├── AGENTS.md                    # 本文件
├── .gitignore
├── start_services.sh           # 一键启动脚本
├── README.md                    # 面向人的项目说明
│
├── server/                      # FastAPI 后端（:8788）
│   ├── main.py                  # 入口，注册 8 个 router
│   ├── config.py                # 配置（端口、CORS、路径常量）
│   ├── db.py                    # 论文 SQLite 操作
│   ├── db_live.py               # Live 模块 SQLite 操作
│   ├── live/                    # Live 安全模块（stream_token）
│   ├── routers/                 # 8 个路由模块
│   │   ├── papers.py            # 论文路由
│   │   ├── management.py        # 项目管理路由（只读 Markdown）
│   │   ├── evaluation.py        # 评测路由
│   │   ├── training.py          # 训练路由（mmaction2）
│   │   ├── speedrun.py          # Speed Run 路由
│   │   ├── datasets.py          # 数据集路由
│   │   └── live.py              # Live 路由（摄像头源 + SSE 推理）
│   ├── parsers/                 # Markdown 解析器
│   └── utils/                   # 工具函数
│
├── web/                         # Vue 3 前端（:3000，代理 /api → 8788）
│   ├── vite.config.js           # Vite 配置
│   └── src/
│       ├── api/                 # API 请求封装（papers, training, live 等）
│       ├── layouts/             # 布局组件
│       ├── router/              # 路由配置
│       ├── views/
│       │   ├── Home.vue          # 首页
│       │   ├── Live.vue          # 实时视频流 + 推理
│       │   ├── papers/           # 论文列表、详情、数据源
│       │   ├── management/       # 团队、报表、任务、里程碑、会议、文档
│       │   ├── evaluation/       # 评测结果
│       │   ├── training/         # 训练配置、数据集、模型、运行、结果
│       │   └── datasets/         # 数据集管理
│       └── components/
│           ├── common/          # 通用组件
│           └── live/             # Live 专用组件（VideoPlayer, SourceManageModal, PtzJoystick）
│
├── configs/                     # mmaction2 训练 config（含 hooks/ 自定义 hook）
├── models/
│   └── mmaction2/               # vendored mmaction2 快照（只读，勿直接改）
│
├── datasets/                    # 数据集目录
│   └── quadruped_action/        # 四足动物动作数据集
│
├── tests/                      # 项目自动化测试（夹具在 results/tests/）
├── scripts/                    # 正式入口 + 分类工具
│   ├── checks/                 # 环境/模型预检、烟测和核验
│   ├── migration/              # 部署、迁移、环境恢复
│   ├── train_model.py           # 训练包装
│   ├── run_test.py              # 正式测试
│   ├── speedrun.py              # Speed Run 批量
│   ├── inference.py             # 单视频推理
│   ├── _infer.py                # 共享推理 + cv2 标注
│   ├── download_checkpoint.py   # 下载预训练权重
│   ├── live_analyze.py          # Live SSE 推理
│   ├── vlm_infer.py             # VLM 推理
│   ├── run_test_vlm.py          # VLM 测试
│   └── ...
│
├── management/                 # 项目管理 Markdown
│   ├── team/                    # 团队成员
│   ├── daily/                   # 日报
│   ├── weekly/                 # 周报
│   ├── monthly/                # 月报
│   ├── meetings/               # 会议纪要
│   ├── milestones.md           # 里程碑
│   ├── projects/               # 项目树 + tasks.json
│   └── docs/                   # Wiki 文档
│
├── papers/                      # 论文模块（config/docs/scripts 子目录）
├── evaluation/                  # 评测模块（configs/datasets/models/outputs/scripts）
├── results/                     # 产物目录
│   ├── training/               # 训练产物（metrics.json, test_results.json, checkpoints/）
│   ├── speedrun/                # Speed Run 产物（outputs/, results.json）
│   ├── live/                   # Live 产物
│   └── skeleton/               # 骨架提取产物
├── data/                        # 运行时数据
│   ├── extracted_papers.json    # 从博客提取的论文列表
│   └── papers.db                # 论文 SQLite 数据库
├── live/                        # Live 模块数据（screenshots/）
├── checkpoints/                 # 预训练 + 训练 checkpoint（gitignore）
├── docs/                        # 设计文档
├── third-party/                 # 第三方集成（pet-videos, remix-petra）
├── .claude/                     # 项目级 skills 和 agents（随仓库版本管理）
│   └── skills/                  # 14 个 skill
└── package-lock.json
```

## 核心模块

### 1. 论文模块 (`papers/`, `server/routers/papers.py`)

- 从博客仓库提取论文，存入 SQLite
- 支持搜索/筛选/收藏/置顶/笔记
- 详情浮窗 + URL hash 持久化

### 2. 训练模块 (`training/`, `server/routers/training.py`)

- 基于 mmaction2 框架
- 支持四种训练模式（从头/预训练/加载权重/断点续训）
- 21 个 mmaction2 模型族注册
- 远程服务器执行（pet RTX 4090）

### 3. 评测模块 (`evaluation/`, `server/routers/evaluation.py`)

- 模型管理 + 数据集管理
- 正式测试（top1/top5）+ speed run
- VLM（Qwen3-VL-Plus）集成
- 结果对比

### 4. Live 模块 (`live/`, `server/routers/live.py`)

- 摄像头源 CRUD（stream_url + storage_path）
- 视频流代理（stream_token 安全签名）
- SSE 实时推理（逐段输出 top-k + 状态）
- 截屏上传管理

### 5. 项目管理模块 (`management/`, `server/routers/management.py`)

- 团队成员、日报/周报/月报
- 任务看板、里程碑、会议纪要
- Wiki 文档
- **后端只读**，脚本直接改文件

## 数据库结构

### papers 表
```sql
id, title, title_zh, abstract, abstract_zh, authors (JSON),
published_at, crawled_at, url, pdf_url, source, external_ids (JSON),
summary_zh, relevance_score, llm_classification (JSON), metadata (JSON),
arxiv_categories (JSON), starred (int), pinned (int), blog_url, note
```

**注意**：`authors` 字段是 JSON 数组字符串（如 `["Author A", "Author B"]`），`server/db.py` 用 `json.loads()` 解析。

### Live 模块（db_live.py）
```sql
-- stream_sources 表
id, name, alias, stream_url, storage_path, is_active, created_at, updated_at

-- screenshots 表
id, source_id, filename, note, created_at
```

## 工作纪律：三阶段流程（Plan → Review → Apply）【最高优先级】

所有工作（代码、脚本、数据管线、服务器配置、文档之外的任何**执行性动作**）一律分为三个阶段：

1. **Plan（Agent 做）**：先写 OpenSpec change（proposal/specs/design/tasks），把"要做什么、怎么做、验收标准"完整落到 plan 里。
2. **Review（用户做）**：用户审核 change。**未获得用户明确批准前，不得执行任何实施性动作**（包括：装环境、下载数据/权重、改代码、改配置、操作远程服务器）。
3. **Apply（Agent 做）**：用户批准后（如 `/openspec-apply-change` 或明确指示）才开工，实施中按 tasks 勾选进度。

**禁止事项**：
- 禁止"先斩后奏"：任何探索性操作（临时环境、clone/下载、跑 demo）若属于计划内工作的一部分，也必须先写入 change 并获批准。
- 纯只读调研（读代码、查论文、搜索 API）不受此限制，但其**结论必须沉淀回 plan**，不允许基于未沉淀的结论直接开工。
- 用户聊天中的口头想法 ≠ 批准；只有对 change 的明确批准（"开始"/"apply"/"批准"）才可进入 Apply。

## 开发规范

### Git 工作流

1. **每次功能变更都应提交**，不要积累大量未提交变更
2. **提交信息格式**：`<type>: <描述>`
3. **type 取值**：feat（新功能）、fix（修复）、refactor（重构）、style（样式）、docs（文档）、chore（杂项）
4. **禁止提交**：`node_modules/`、`__pycache__/`、`.venv/`、`*.db`、`data/papers.db`、`results/`、`checkpoints/`、`live/screenshots/`

#### 交付到 pet

`pet` 是本项目的 GPU 远程，remote 为 `pet:pet-action-recognition`（`~/.ssh/config` 中的 SSH alias）。交付规则：

1. **代码只走 Git**：本地 `commit` → `git push pet <branch>` → 在远程显式 checkout 并校验 commit（`git rev-parse HEAD` 与所推分支对齐），**确认后再启动服务**；不要假设“推上去就自动部署了”。
2. **禁止 `rsync` / `scp`** 把本地工作区文件同步到远程部署目录；需要验证一个尚未部署的分支时，用 `git -C <远程仓库> worktree add --detach <tmp 路径> <branch>` 在远程物化，验证完 `git worktree remove`。`--detach` 必须带，否则被 worktree 占用的分支 `push` 会失败。
3. **远程临时产物只进 `tmp/`**，不放 `$HOME` 根目录，也不放系统 `/tmp` —— 与「服务器/产物纪律（硬规则）」第 1、2 条同一约束。注意本仓库 `.gitignore` 目前只忽略 `/tmp/*.log`，写到 `tmp/` 的其它文件在提交前必须确认不入库。
4. **连接细节留在 `~/.ssh/config`**：不在仓库脚本、文档或本文件里硬编码 IP、端口、用户名、私钥路径。

### 前端开发

- 框架：Vue 3 `<script setup>` + Naive UI 组件库
- 样式：SCSS，组件内 `<style scoped>`
- API 请求：通过 `web/src/api/` 封装
- 路由：`web/src/router/index.js`
- 布局：`web/src/layouts/MainLayout.vue`

### 后端开发

- 框架：FastAPI，路由在 `server/routers/`
- 配置：`server/config.py`
- 数据库：`server/db.py`（论文）、`server/db_live.py`（Live）
- Python 版本：`python3` 3.13
- 管理路由直接读写 Markdown 文件

### Skill 管理

- **项目级 skill 放在 `.claude/skills/`**（随仓库版本管理）
- **跨项目通用 skill 放在 `~/.claude/skills/`**
- `.agents/` 是 `.claude/` 的软链接

### 测试、预检与迁移脚本的目录规范

#### 自动化测试

项目自动化测试（`test_*.py`）放在 `tests/`，按模块组织。

#### 预检与迁移工具

环境检查、模型预检、烟测及产物核验命令放在 `scripts/checks/`；代码/数据部署、迁移、环境恢复和同步工具放在 `scripts/migration/`。

#### 正式入口与产物

正式训练、推理、评测、数据准备及分析入口保留在 `scripts/`。测试夹具、预检报告、审计及实验产物放在不入库的 `results/`。

- 不把测试放进 `models/mmaction2/tests/`；该目录属于只读第三方快照。
- 测试夹具与临时输出使用项目 `results/tests/` 下的独立目录，结束后安全清理，不依赖系统临时目录。
- 移动脚本必须同步修正仓库根目录定位、Python 导入、调用路径和当前操作文档；保留旧实验配置、日志及历史记录中的原始路径。
- 已归属某个 skill 的脚本继续由该 skill 管理；以上规范用于项目自身脚本，不将 skill 工具重复复制到顶层。
- 远程已有权重可在 `checkpoints/` 下按实验/模型建立软链接；不得覆盖既有文件或修改源权重，机器绝对路径链接不入 Git。

### 当前项目 Skill（15 个）

| Skill | 路径 | 用途 |
|-------|------|------|
| repo-structure | `.claude/skills/repo-structure/` | 仓库文件组织、目录结构、模块路由 |
| datasets | `.claude/skills/datasets/` | 数据集与预训练权重管理 |
| design-principles | `.claude/skills/design-principles/` | UI/UX 设计原则 |
| documentation | `.claude/skills/documentation/` | 文档写作指南 |
| evaluation | `.claude/skills/evaluation/` | 评测体系模块（mmaction2 动作识别） |
| live | `.claude/skills/live/` | 实时视频流 + SSE 推理 |
| management | `.claude/skills/management/` | 项目管理 CRUD |
| papers | `.claude/skills/papers/` | 论文收集模块 |
| remote-servers | `.claude/skills/remote-servers/` | 远程服务器使用 |
| testing | `.claude/skills/testing/` | 测试/speed run/推理 |
| training | `.claude/skills/training/` | mmaction2 训练 |
| upstream-sync | `.claude/skills/upstream-sync/` | 上下游仓库同步 |
| using-mmaction2 | `.claude/skills/using-mmaction2/` | mmaction2 深度指南 |
| web | `.claude/skills/web/` | Web 全栈开发 |
|  |  |  |

### 服务器/产物纪律（硬规则）

1. **可复用脚本必须先进仓库**：任务中产生的脚本先按上述规范提交到 `scripts/`、其分类子目录或 `tests/`（入版本管理）再执行；**禁止在 `/tmp` 放脚本**（历史事故：multi_detect / kp_video / compare_mc 三次返工）
2. **分析产物入项目路径**：数据/审计/报告类产物一律写项目内路径（服务器上 `~/pet-action-recognition/results/...` 或仓库 `results/`），**禁止散落 `$HOME` 根目录或 `/tmp`**（历史事故：saturation_audit.json 丢 home 被用户指正）
3. **远程进程检查防自匹配**：`pgrep -f <关键词>` 会匹配到检查命令自身导致误报 RUNNING——用日志标志（如 BATCH DONE）、完整路径匹配或 `ps aux | grep keyword | grep -v grep`
4. **远程后台启动同样必须 `</dev/null`**：`nohup cmd </dev/null > log 2>&1 & disown`——漏掉会导致 ssh 会话挂起超时（即使输出已重定向）

### macOS 后台进程

```bash
# 启动后台进程（必须用 </dev/null 防止挂起）
nohup cmd </dev/null > /tmp/log 2>&1 & disown

# 检查进程
ps aux | grep <keyword> | grep -v grep

# 检查端口
lsof -i :<port>
```

## 常见问题

### 前端启动后立即挂起（进程状态为 T）
macOS 上 nohup 进程需要 `</dev/null` 重定向 stdin。

### Vite 端口被占用
使用 `--strict-port` 避免自动 fallback 到其他端口。

### 论文列表为空
检查后端（port 8788）是否在运行，`data/papers.db` 是否存在且有数据。

### 训练/测试必须在远程服务器
**绝不在本地跑训练、测试、推理**（本地无 GPU）。所有 GPU 活必须在 pet（RTX 4090）或 A100 上执行。

## Reusable pipeline code

Reusable capabilities and formal `python -m` entry points belong in `lib/`; scripts remain appropriate for probes, checks, and migration tools.
