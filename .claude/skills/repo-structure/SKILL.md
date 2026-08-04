---
name: repo-structure
description: 'Use when asked how the pet-action-recognition repo is organized — where a file or feature lives, what each top-level directory does, how frontend/backend/data/training fit together, or before navigating an unfamiliar part of the codebase. Triggers (CN+EN): "文件组织", "目录结构", "项目结构", "这个库怎么搭的", "某文件在哪", "X 放在哪个目录", "codebase layout", "repository structure", "where does X live".'
---

# 仓库结构 / Repo Structure

## 这是什么
pet-action-recognition 仓库的**导航地图**。一句话定位每个顶层目录的职责、前后端 / 数据 / 训练如何拼在一起，并指明要"做"某件事时该切到哪个模块 skill。

## 何时用 / When to use
- 被问"这个库怎么组织的 / 目录结构 / 项目结构 / 某文件在哪 / codebase layout"
- 进入不熟悉的模块前，想先建立全局图
- 决定一个**新文件该放哪**
- **不该用**：要在某个模块里做 CRUD / 跑训练 / 开发页面 —— 直接用对应模块 skill（见「模块路由」表）

## 顶层布局（2026-07-31 核实）

```
pet-action-recognition/
├── server/                     # FastAPI 后端（:8788）
│   ├── main.py                 # 入口，注册 6 个 router；config.py = 端口/CORS/路径常量
│   ├── db.py                   # 论文 SQLite 操作
│   ├── routers/                # papers / management / evaluation / training / speedrun / datasets
│   ├── parsers/                # management/ Markdown 解析器（tasks/team/report/milestones/projects/markdown_table）
│   └── utils/file_utils.py
├── web/                        # Vue3 + Vite + Naive UI 前端（:3000，代理 /api → 8788）
│   └── src/{api, views, components, layouts, router, stores, styles, assets}
│        └── views/{papers, management, evaluation, training, datasets}
├── configs/                    # mmaction2 训练 config（quadruped/pet_mammal 系列）
│   └── hooks/                  # 自定义 hook：vis_samples_hook.py、label_smooth_loss.py
├── models/mmaction2/           # vendored 训练框架（只读快照，sha a5a167d，别直接改）
├── datasets/quadruped_action/  # 四足合成数据集清单（train/val/test list + classes.txt + README）
├── scripts/                    # 顶层脚本：train_model / run_test / inference(+_infer) / speedrun /
│                               #   generate_synthetic_quadruped / import_papers / export_papers /
│                               #   download_checkpoint / pet_repin.sh
├── management/                 # 项目管理 Markdown（team/daily/weekly/monthly/meetings/docs/projects/milestones.md）
├── papers/                     # 论文搜集：config/docs/scripts 三个子目录均为空壳（只有 .gitkeep）
├── evaluation/                 # 评测：configs/datasets/models/outputs/scripts 均为空壳（只有 .gitkeep）
├── data/                       # 运行时数据：extracted_papers.json（导入源）、papers.db（SQLite，gitignore）
├── docs/plans/                 # 设计文档（2026-07-13 mmaction2 训练集成方案）
├── .claude/{agents,skills}     # 项目级 skill 与 agent（随仓库版本管理，13 个 skill）
├── .agents/{agents,skills}     # .claude/ 的镜像（同 13 个 skill + description-writer agent）
├── AGENTS.md                   # 权威架构说明（技术栈/服务架构/目录结构/开发规范）
├── README.md                   # 面向人的项目说明（目录结构描述已漂移，以本文件为准）
└── start_services.sh           # 一键启动（后端 8788 + 前端 3000）
```

注意：`results/`（训练/测试/speedrun 产物）与 `checkpoints/`（权重）在 `server/config.py` 中定义，但本机磁盘上**尚不存在**，首次跑训练时创建，且已 gitignore。

## 请求流 / Request flow

```
浏览器 → Vite(:3000, 代理 /api) → FastAPI(:8788) → SQLite(data/papers.db)
                                              ↘ FastAPI → management/ Markdown（只读 GET）
                                              ↘ FastAPI → datasets/ + results/training/（训练/测试/推理/speedrun）
```

- **前端**：Vue3 SPA，Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，直接操作 SQLite；management 路由只读解析 Markdown
- **DB**：本地 SQLite，独立于任何外部服务
- **训练**：routers/training.py 内联 `_MMACTION2_REGISTRY`，subprocess 调 `scripts/train_model.py` 等，产物落 `results/training/`

## 模块路由（要"做"事，切到对应 skill）

| 任务 | Skill |
|------|-------|
| 训练 / finetune / checkpoint 管理 | training |
| 测试 / speed run / 单视频推理 | testing |
| mmaction2 安装 / config 系统 / 适配 registry | using-mmaction2 |
| 数据集 / 预训练权重下载与组织 | datasets |
| 远程训练机（pet / A100）使用 | remote-servers |
| 评测模块（模型/数据集/评测配置，目前为空壳） | evaluation |
| 论文导入 / 分类 / 笔记 | papers |
| 团队 / 报表 / 任务 / 会议 CRUD | management |
| 前后端开发 / 启动 / 调试 | web |
| UI/UX 设计规范（新页面/列表/可视化） | design-principles |
| 文档写作规范（Wiki/Mermaid） | documentation |
| 上游 / 下游四库 git 同步 | upstream-sync |

## 权威来源（需要更细时去读）
- **`AGENTS.md`** ——「目录结构 / 服务架构 / 开发规范」；AI agent 的主参考，最全
- **`docs/repo-overview.md`** —— 仓库全景文档（模块详解 + 已知问题清单）
- **`README.md`** —— 面向人的项目说明（目录结构段已漂移）
- **`management/docs/projects/pet-action-recognition/README.md`** ——「项目树」进展（持续更新）

## 常见坑
- `models/mmaction2/` 是 **vendored 快照**，不要在仓库里直接改它；本地修改通过 `configs/hooks/` + `custom_imports` 注入，升级走 using-mmaction2 的 vendor 流程
- **项目级 skill 必须放 `.claude/skills/`**（随仓库走），不要放 `~/.claude/skills/`（那是跨项目通用 skill）；`.agents/skills/` 是其镜像
- `data/papers.db`、`results/`、`checkpoints/`、`papers/data/`、`papers/cache/` 已 gitignore —— 换机器需重新生成/导入
- `evaluation/` 与 `papers/{config,docs,scripts}` 目前是**空壳目录**（只有 `.gitkeep`），真实评测走 training/run_test 流水线
- `datasets/quadruped_action/` 的注解指向不存在的 `videos_*` 目录（status: pending_collection）；真实数据集 `pet_action_mammal_v0` 在远程训练机
- 目录树可能滞后于实际代码；以 `AGENTS.md` + 实际 `ls` 为准
