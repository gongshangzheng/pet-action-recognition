---
title: 交接与协作指南
author: 郑鑫裕
date: 2026-09-16
tags: [交接, 上手, 工作纪律, 远程, GPU, 安全]
summary: 新协作者单一上手入口——速览快照/环境搭建/工作纪律/协作约定/FAQ/安全红线
id: 11
---

# 交接与协作指南

> **读者画像**：本套文档面向三类读者——① 新加入项目的协作者 ② AI Agent（接手项目时）③ 未来的我自己。所有"读一遍能上手"的内容都在这里。
>
> **凭证处理原则**：本文档**不写任何明文凭证/密码/SSH 密钥/API Key**——只写"去哪找"。具体凭证在 `.claude/skills/remote-servers/` 内的服务器 README 与本地密码管理器。

## §1 项目速览与当前阶段

### §1.1 一句话

**宠物动作识别研究平台**——管理动作识别相关论文、团队协作、模型训练与实时推理，目标是建立"从监控视频到猫在做什么"的完整管线。

### §1.2 当前进度快照（基准日 2026-09-16）

| 主线 change | 进度 |
 | | |
| `batch-followcam-extraction` | 5/6 待归档（34/34 已完成） |
| `video-feature-latent` | 1/14（行为表征选型中） |
| `spot-check-cli` | 0/4（待前置） |
| `identity-action-tokenizer` | 0/9（研究型，FLOAT 式参考输入 + 正交运动基）|

日常进度变动看 `management/projects/*/tasks.json`（任务看板）。

### §1.3 11 月中期验收 KPI

来自 2026-08-15 二期计划（已整合到 [6 号《系统架构》§9.3](../wiki/architecture)）：

- P0 精度攻坚：8-9 月，5 个训练 run 全 error（数据/接口问题），k400 烟测 top1 0.77 已验证管线
- P1 端侧 pipeline：9-11 月，34 段白天已处理，夜间红外段待做
- P2 部署验收：11-12 月

## §2 环境搭建

### §2.1 本地（macOS）

**一键启动**：

```bash
cd ~/pet-action-recognition
bash start_services.sh
# 后端 8788 + 前端 3000
```

**手动启动**：

```bash
# 后端
nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8788 </dev/null > /tmp/backend.log 2>&1 & disown

# 前端
cd web && nohup npx vite --port 3000 --strict-port </dev/null > /tmp/frontend.log 2>&1 & disown
```

**前端端口冲突**：使用 `--strict-port` 避免 fallback。如 3000 占用，先 `lsof -i :3000` 找占用进程再 kill。

**前端启动后立即挂起（T 状态）**：macOS nohup 缺 `</dev/null>` 会挂——已写在 `start_services.sh`。

### §2.2 远程服务器

> **远程服务器只用来执行，不要在那里开发或修改代码**。所有代码改动都在本地完成，经 git push 同步。

**连接方式 / IP 重 pin / 端口转发** 详见 `.claude/skills/remote-servers/`（**本节不复制凭证信息**）。

- pet：2× RTX 4090，已搭好 mmaction2 环境，主要跑训练/批处理
- A100：≥4× A100-80GB，待启用

**重要**：

- `ssh pet` 之前必读 `.claude/skills/remote-server-discipline`——远程纪律硬规则
- 所有改动本地完成 → git commit → git push → 远程 git pull

### §2.3 NAS

- 挂载在 pet 上
- UCF101 等大语料放 NAS
- 具体挂载路径见 `remote-servers` skill

### §2.4 conda 环境（pet）

- `mmaction2`：训练用
- `plf`：GroundingDINO/HQSAM/ViTPose 管线用（独立环境，避免 mmcv 冲突）
- `pet_tokenizer`：tokenizer 训练/推理用（原 `pet_vjepa`，2026-09-16 按用途改名；需 transformers ≥4.55）

环境隔离纪律详见 [6 号 §5.1](../wiki/architecture) D5。

## §3 工作纪律（三阶段 OpenSpec + 远程纪律）

### §3.1 三阶段 OpenSpec 流程

> **最高优先级**——所有执行性动作（代码、脚本、数据管线、服务器配置）一律三阶段。

1. **Plan（Agent 做）**：先写 OpenSpec change（`openspec new change <name>`），把"做什么/怎么做/验收"落到 plan
2. **Review（用户做）**：用户审 change。**未获批准前不动手**
3. **Apply（Agent 做）**：批准后用 `openspec-apply-change` skill 实施，按 tasks 勾选

**禁止**：

- 先斩后奏（"装环境/下数据"等即便为了 plan 验证也必须先入 change 获批）
- 把"用户聊天中的口头想法"当成批准——只有对 change 的明确批准才生效

**OpenSpec skills 位置**：`.pi/skills/openspec-{propose,apply,archive,sync,update,explore}/`

### §3.2 远程服务器纪律（硬规则）

> 出自 `.claude/skills/remote-server-discipline/`——动手 ssh 之前先读它。

1. **远程 = 只读执行环境**——所有文件改动本地完成，git push 同步
2. **脚本先进仓库**——任务中产生的脚本先 commit 到 `scripts/`，再执行
3. **产物入项目路径**——禁止散落 `$HOME` 或 `/tmp`
4. **进程检查防自匹配**——`pgrep -f` 会匹配命令自身，用日志标志/完整路径
5. **后台启动必带 `</dev/null>`**——漏了 macOS ssh 挂起

### §3.3 GPU 共享纪律（pet 2× RTX 4090）

- 训练前 `nvidia-smi` 看显存占用
- 不一次性占满两卡
- 大模型（V-JEPA 2）走 bf16 + 梯度检查点

### §3.4 安全红线

- ❌ 不把 API Key/密码写入代码
- ❌ 不在本地跑训练/测试（本地无 GPU）
- ❌ 不直接改远程文件
- ❌ 不把数据集/结果提交到错误的位置
- ✅ 敏感配置走环境变量（`.env` / CI secrets）

## §4 协作约定

### §4.1 Git 工作流

**提交信息格式**：

```
<type>: <description>
```

**type 取值**：
- `feat` 新功能
- `fix` 修复
- `refactor` 重构
- `style` 样式
- `docs` 文档
- `chore` 杂项

**禁止提交**：
- `node_modules/`、`__pycache__/`、`.venv/`
- `*.db`、`data/papers.db`
- `results/`、`checkpoints/`、`live/screenshots/`

### §4.2 文档维护责任

| 文档 | 维护者 |
|---|---|
| 本套 11 篇 wiki | 郑鑫裕 + change 实施时同步更新 |
| `management/{daily,weekly,monthly,meetings}/` | 各自负责 |
| `management/team/` | 人事变动时更新 |
| `openspec/changes/<name>/` | 该 change 负责人 |
| `.claude/skills/` | agent 工具维护者 |
| `AGENTS.md` | 项目级指令变更时更新 |

### §4.3 任务看板

- `management/projects/pet-action-recognition/tasks.json`
- `management/projects/projflow/tasks.json`
- 实时数据，不是文档

### §4.4 周报 / 日报 / 月报

- 周报：周五前写完 `management/weekly/<n>.md`
- 月报：月末 `management/monthly/<n>.md`
- 日报（可选）：`management/daily/<n>.md`

## §5 FAQ（高频问题排查入口）

| 问题 | 排查入口 |
|---|---|
| 服务起不来 | `start_services.sh` + `/tmp/backend.log` + `/tmp/frontend.log` |
| 前端 3000 占用 | `lsof -i :3000` → kill |
| 前端 T（挂起 | `start_services.sh` 是否带 `</dev/null>` |
| 后端 8788 报错 | `/tmp/backend.log` 末尾 + `server/main.py` |
| 论文列表为空 | 后端运行？`data/papers.db` 存在？ |
| 连不上 pet | `.claude/skills/remote-servers/` |
| 训练报错 | [4 号《训练体系》](../wiki/training-guide) §6 + `.claude/skills/training/` |
| 批处理报错 | [7 号《身份标识与检索》](../wiki/identity-and-retrieval) §1.4 + `.claude/skills/live/` |
| 推理报错 | `.claude/skills/testing/` |
| Speed Run 问题 | `.claude/skills/speedrun/` |
| 文档找不到 | [1 号《仓库资产盘点》](../wiki/repo-inventory) 导航表 |

## §6 风格与约定（贯穿本套 11 篇 wiki）

> 本套 11 篇 wiki 严格遵守"老师腔"风格：

1. **老师腔**：每段先点目的（"为什么有这一步"），再讲方法，最后给坑
2. **术语首次出现必定义**：括注（"X（…）"）或紧跟一句通俗定义
3. **架构文档带术语表**：[6 号《系统架构》§0](../wiki/architecture) 是范例
4. **类比与示例**：抽象概念配生活类比
5. **避免**：缩写堆叠、长从句、"显然"之类的不解释
6. **结论带四要素**（D6）：日期/来源/关键数字/证据路径

---

## §7 上手速查（30 分钟版）

1. **读**：[1 号《仓库资产盘点》](../wiki/repo-inventory) 5 分钟
2. **看图**：[6 号《系统架构》§3 端到端总图](../wiki/architecture) 3 分钟
3. **跑起来**：`bash start_services.sh`，打开 http://localhost:3000 看一眼 5 分钟
4. **看训练**：[4 号《训练体系》](../wiki/training-guide) 8 分钟
5. **看管线**：[7 号《身份标识与检索》](../wiki/identity-and-retrieval) 8 分钟
6. **试一把**：在 pet 上跑一个 k400 烟测（详见 [4 号 §6](../wiki/training-guide)）

之后就可以开 OpenSpec change 做第一个任务了。

---

**配套**：[1 号《仓库资产盘点》](../wiki/repo-inventory)（资产索引）/ [6 号《系统架构》](../wiki/architecture)（结构总览）/ `.claude/skills/remote-servers/`（远程服务器）/ `.claude/skills/remote-server-discipline`（远程纪律）/ `.claude/skills/training/`（训练操作）/ `.claude/skills/live/`（Live 操作）/ `.claude/skills/speedrun/`（Speed Run）/ `.claude/skills/testing/`（测试）/ `.claude/skills/management/`（项目管理）/ `.claude/skills/papers/`（论文）/ `.claude/skills/datasets/`（数据集）/ `.claude/skills/evaluation/`（评测）/ `.claude/skills/upstream-sync/`（上下游同步）/ `.claude/skills/using-mmaction2/`（mmaction2 深度指南）/ `.claude/skills/repo-structure/`（仓库结构）