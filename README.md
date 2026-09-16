# Pet Action Recognition

> **宠物动作识别研究平台**——管理动作识别相关论文、团队协作、模型训练与实时推理。
>
> **文档入口**：[`management/docs/repo-inventory.md`](management/docs/repo-inventory.md)（仓库资产盘点，全库唯一入口）；完整 wiki 共 11 篇，详 `management/docs/`。

## 项目背景

本项目研究家养宠物（以猫为主）的动作识别：从监控视频自动判断"猫在做什么"（吃/喝/睡/跑/异常等）。涵盖三件事子子任务：

1. **定位与跟踪**（`pet-motion-latent-pipeline` 总管 change）
2. **动作表征与无监督发现**（`video-feature-latent`）
3. **身份识别与物体实例识别**（`identity-action-tokenizer` + `registry-retrieval`）

## 项目结构

```
pet-action-recognition/
├── server/                      # FastAPI 后端（:8788）
├── web/                         # Vue 3 前端（:3000）
├── configs/                     # mmaction2 训练配置
├── models/mmaction2/            # vendored mmaction2（只读）
├── petlib/                      # 管线可替换模块
├── datasets/                    # 数据集（cats v1 等）
├── scripts/                     # 训练/测试/推理/批处理脚本
├── checkpoints/                 # 本地空目录（权重在远程 pet 服务器）
├── results/                     # 训练/测试/批处理产物
├── live/                        # Live 模块数据
├── data/                        # 论文库 + 备份
├── management/                  # 项目管理 + Wiki（11 篇）
│   ├── docs/                    # 本套 wiki 11 篇
│   ├── projects/                # 项目树 + tasks.json
│   ├── daily/weekly/monthly/    # 报表
│   ├── meetings/                # 会议纪要
│   └── team/                    # 团队成员
├── papers/                      # 论文模块
├── evaluation/                  # 评测模块
├── openspec/                    # OpenSpec change 体系
│   ├── changes/                 # 活跃 change
│   ├── specs/                   # 主 spec
│   └── archive/                 # 归档 change
├── docs/                        # 设计文档
├── third-party/                 # 第三方库借鉴
├── templates/                   # 模板
└── .claude/skills/              # agent 技能（15 个）
```

## 各模块说明

### 八大模块

| 模块 | 端口/路径 | 说明 |
|---|---|---|
| **Papers 论文搜集** | `server/routers/papers.py` / `web/src/views/papers/` | 239 篇论文库（SQLite）、分类筛选、笔记 |
| **Training 训练** | `server/routers/training.py` / `web/src/views/training/` | mmaction2 训练，4 种模式，远程执行 |
| **Evaluation 评测** | `server/routers/evaluation.py` / `web/src/views/evaluation/` | 正式测试 + 速度测试 + VLM |
| **Speed Run** | `server/routers/speedrun.py` / `web/src/views/evaluation/SpeedRun.vue` | 批量标注视频 + 烟测指标 |
| **Live 直播** | `server/routers/live.py` / `web/src/views/Live.vue` | 摄像头源管理 + SSE 实时推理 |
| **Management 项目管理** | `server/routers/management.py` / `web/src/views/management/` | 团队/日报/周报/月报/会议/任务/里程碑/Wiki |
| **Datasets 数据集** | `server/routers/datasets.py` / `web/src/views/datasets/` | 数据集浏览 |
| **Pipeline 管线** | openspec changes | pet-motion-latent-pipeline 总管 + 子 change |

### Wiki 11 篇（`management/docs/`）

1. **仓库资产盘点**（你正在读的这个 README 的扩展版）
2. 数据集全景
3. 模型（重要模型逐个条目：简介 + 实测结果）
4. 训练体系
5. Live 模块
6. **系统架构**（完整结构 + 未来计划）
7. **身份标识与检索**（定位追踪 + 猫 Re-ID + RAG 式物体标识）
8. **身份-动作 Tokenizer 专篇**（FLOAT×TiTok 杂交）
9. 研究结论与踩坑
10. 第三方项目借鉴
11. 交接与协作指南

详见 [仓库资产盘点](management/docs/repo-inventory.md)。

### Claude Code Skills（15 个，`.claude/skills/`）

- 仓库结构 / 数据集 / 设计原则 / 文档
- 评测 / Live / 项目管理 / 论文
- 远程服务器（纪律）
- 测试 / Speed Run / 训练 / 上游同步
- mmaction2 深度指南 / Web 全栈

详细见 `.claude/skills/` 与 [交接与协作指南](management/docs/handover-guide.md)。

## 快速开始

```bash
# 克隆仓库
git clone <repo-url>
cd pet-action-recognition

# 一键启动（后端 8788 + 前端 3000）
bash start_services.sh

# 打开网页
open http://localhost:3000
```

各模块独立使用，详见各子目录说明与本仓库 wiki 11 篇（从 [仓库资产盘点](management/docs/repo-inventory.md) 开始读）。

## 工作纪律

1. **三阶段 OpenSpec 流程**（最高优先级）：Plan → Review → Apply
2. **远程服务器只读**：所有改动本地完成 → git push → 远程 git pull
3. **不写明文凭证**：API Key 等走环境变量
4. **GPU 共享**：训练前 `nvidia-smi` 看显存，不一次性占满两卡
5. **脚本先进仓库**：禁止 `/tmp` 放脚本
6. **完整纪律**见 [交接与协作指南](management/docs/handover-guide.md) 与 `AGENTS.md`

## 文档与 OpenSpec

- **本仓库 wiki 11 篇**：`management/docs/`（按 frontmatter `id` 1-11 排序）
- **OpenSpec change 体系**：`openspec/changes/`（活跃）+ `openspec/specs/`（主 spec）
- **agent skills**：`.claude/skills/`（agent 操作指南，与 wiki 分工）

详细说明见 [仓库资产盘点](management/docs/repo-inventory.md)。