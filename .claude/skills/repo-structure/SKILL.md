---
name: repo-structure
description: |
  仓库文件组织、目录结构、模块路由（导航入口）。用于定位文件、理解模块关系。
  触发场景 (CN+EN)："文件组织"、"目录结构"、"项目结构"、"这个库怎么搭的"、"某文件在哪"、"X 放在哪个目录"、"codebase layout"、"repository structure"、"where does X live"。
---

# 仓库结构 / Repo Structure

## 这是什么
pet-action-recognition 仓库的**导航地图**。定位每个顶层目录的职责、前后端 / 数据 / 训练如何拼在一起，并指明要"做"某件事时该切到哪个模块 skill。

## 何时用
- 被问"这个库怎么组织的 / 目录结构 / 项目结构 / 某文件在哪 / codebase layout"
- 进入不熟悉的模块前，想先建立全局图
- 决定一个新文件该放哪
- **不该用**：要在某个模块里做 CRUD / 跑训练 / 开发页面 —— 直接用对应模块 skill（见「模块路由」表）

## 顶层布局（2026-08-04 核实）

```
pet-action-recognition/
├── server/                     # FastAPI 后端（:8788）
│   ├── main.py                 # 入口，注册 8 个 router
│   ├── config.py               # 端口/CORS/路径常量
│   ├── db.py                   # 论文 SQLite 操作
│   ├── db_live.py              # Live 模块 SQLite 操作
│   ├── live/                   # Live 安全模块（stream_token）
│   ├── routers/                # 8 个路由
│   │   ├── papers.py           # 论文 CRUD
│   │   ├── management.py       # 项目管理（只读 Markdown）
│   │   ├── evaluation.py       # 评测配置
│   │   ├── training.py         # 训练（mmaction2 registry）
│   │   ├── speedrun.py         # Speed Run
│   │   ├── datasets.py         # 数据集管理
│   │   └── live.py             # 实时视频流 + SSE 推理
│   ├── parsers/                # Markdown 解析器
│   └── utils/                  # 工具函数（file_utils 等）
│
├── web/                        # Vue3 + Vite + Naive UI（:3000）
│   ├── vite.config.js          # 端口 3000，代理 /api → 8788
│   └── src/
│       ├── api/                # API 请求封装（papers, training, live, datasets, evaluation, management）
│       ├── layouts/            # MainLayout.vue（侧边栏 + 内容）
│       ├── router/index.js     # 路由配置
│       ├── views/
│       │   ├── Home.vue        # 首页
│       │   ├── Live.vue        # 实时视频流 + 推理
│       │   ├── papers/         # 论文列表、详情、数据源
│       │   ├── management/     # 团队、报表、任务、里程碑、会议、文档
│       │   ├── evaluation/    # 评测结果
│       │   ├── training/      # 训练（7 个组件：SpeedRun, TrainConfig, TrainDataset, TrainModel, TrainRun, TrainRunDetail, TrainResults）
│       │   └── datasets/      # 数据集管理
│       └── components/
│           ├── common/         # 通用组件
│           └── live/           # VideoPlayer, SourceManageModal, PtzJoystick
│
├── configs/                    # mmaction2 训练 config（含 hooks/ 自定义 hook）
│
├── models/mmaction2/           # vendored 训练框架（只读快照）
│
├── datasets/                   # 数据集目录（gitignore）
│   └── quadruped_action/       # 四足动物动作数据集
│
├── scripts/                    # 顶层脚本
│   ├── train_model.py          # 训练包装入口
│   ├── run_test.py             # 正式测试包装
│   ├── speedrun.py             # Speed Run 批量
│   ├── inference.py            # 单视频推理
│   ├── _infer.py               # 共享推理 + cv2 标注 + H.264 转码
│   ├── live_analyze.py         # Live SSE 推理脚本
│   ├── vlm_infer.py            # VLM 推理
│   ├── run_test_vlm.py         # VLM 测试
│   ├── download_checkpoint.py  # 下载预训练权重
│   ├── benchmark_speed.py       # 速度基准测试
│   ├── eval_all_k400.py        # K400 全模型评测
│   ├── extract_keypoints_dlc.py # DeepLabCut 骨架提取
│   ├── infer_ap10k_pose.py     # AP-10K 姿态推理
│   └── ...                     # 还有更多
│
├── management/                 # 项目管理 Markdown
│   ├── team/                   # 团队成员 .md
│   ├── daily/                  # 日报 YYYY/MM/DD-{author}.md
│   ├── weekly/                 # 周报 YYYY/W{NN}-{author}.md
│   ├── monthly/                # 月报 YYYY/{MM}-{author}.md
│   ├── meetings/               # 会议纪要 YYYY-MM-DD.md
│   ├── milestones.md           # 里程碑
│   ├── projects/               # 项目树 {slug}/ + tasks.json
│   └── docs/                   # Wiki 文档
│
├── results/                    # 产物（gitignore）
│   ├── training/              # metrics.json, test_results.json, checkpoints/
│   ├── speedrun/              # results.json, outputs/
│   ├── live/                  # Live 产物
│   └── skeleton/              # 骨架提取产物
│
├── data/                       # 运行时数据
│   ├── extracted_papers.json  # 从博客提取的原始数据
│   └── papers.db              # 论文 SQLite（gitignore）
│
├── live/                       # Live 模块数据（gitignore）
│
├── checkpoints/                # 预训练 + 训练 checkpoint（gitignore）
│
├── papers/                     # 论文模块（config/docs/scripts 空壳目录）
│
├── evaluation/                 # 评测模块（configs/datasets/models 空壳）
│
├── docs/                       # 设计文档
│
├── third-party/               # 第三方集成（pet-videos, remix-petra）
│
├── .claude/skills/            # 14 个项目级 skill（随仓库版本管理）
└── AGENTS.md                  # 权威架构说明
```

## 请求流 / Request flow

```
浏览器 → Vite(:3000, 代理 /api) → FastAPI(:8788)
                                       ├─ SQLite(data/papers.db)      # 论文
                                       ├─ management/ Markdown        # 项目管理（只读）
                                       ├─ live/ (db_live + 文件)      # Live 模块
                                       └─ results/ (训练/评测产物)    # 产物服务
```

- **前端**：Vue3 SPA，Vite dev server 代理 `/api` 到后端
- **后端**：FastAPI，直接操作 SQLite；management 路由只读解析 Markdown
- **DB**：本地 SQLite，独立于任何外部服务
- **Live**：摄像头源管理 + 视频流代理 + SSE 推理

## 模块路由（要"做"事，切到对应 skill）

| 任务 | Skill |
|------|-------|
| 训练 / finetune / checkpoint 管理 | [[training]] |
| 测试 / speed run / 单视频推理 | [[testing]] |
| mmaction2 安装 / config 系统 / 适配 registry | [[using-mmaction2]] |
| 数据集 / 预训练权重下载与组织 | [[datasets]] |
| 远程训练机（pet / A100）使用 | [[remote-servers]] |
| 评测模块（模型/数据集/评测配置） | [[evaluation]] |
| 实时视频流 / SSE 推理 | [[live]] |
| 论文导入 / 分类 / 笔记 | [[papers]] |
| 团队 / 报表 / 任务 / 会议 CRUD | [[management]] |
| 前后端开发 / 启动 / 调试 | [[web]] |
| UI/UX 设计规范 | [[design-principles]] |
| 文档写作规范 | [[documentation]] |
| 上游 / 下游四库 git 同步 | [[upstream-sync]] |

## 权威来源

- **`AGENTS.md`** —— 目录结构 / 服务架构 / 开发规范；AI agent 的主参考
- **`server/config.py`** —— 所有路径常量定义
- **`server/routers/`** —— 各模块 API 端点定义
- **`management/docs/projects/pet-action-recognition/README.md`** —— 项目树进展

## 常见坑

| 问题 | 说明 |
|------|------|
| `models/mmaction2/` 是 **vendored 快照** | 不要在仓库里直接改它；本地修改通过 `configs/hooks/` + `custom_imports` 注入 |
| `results/`、`checkpoints/`、`live/`、`data/papers.db` 已 **gitignore** | 换机器需重新生成/导入 |
| 训练/测试/推理 **必须在远程服务器** | 绝不在本地 mac 跑（无 GPU、无 mmaction2 环境） |
| `server/routers/management.py` 是 **只读** | 写操作走 `.claude/skills/management/scripts/` 中的脚本 |
| `papers/`、`evaluation/` 目录是 **空壳** | 真实数据和配置在其他地方（data/、results/） |

## 目录树可能滞后于实际代码

以 `AGENTS.md` + 实际 `ls` 为准。
