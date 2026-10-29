---
name: remote-ops
description: |
  与远程服务器（SSH 别名 pet）交互的唯一指引：容量预检、资源守卫（nice + 线程上限 + 看门狗 kill）、
  代码静态审计与降规模冒烟、部署与代码流转纪律。凡是要在 pet 上跑命令、判断机器是否空闲、
  或在共享机上跑任何超过几秒的任务时使用。其他 skill 只引用这里，不各自重复。
  移植来源：CyberVerse/.agents/skills/remote-ops（2026-10-29）。
---

# 远程交互（pet）统一指引

> **上游关系**：本 skill 已反哺上游 ProjFlow（`521496a [shared]`），上游是**通用版**——
> 不写死服务器，靠 `REMOTE_SSH` / `REMOTE_ROOT` 两个变量配置；**本仓副本填了本仓的实际配置**
> （别名、工作目录、环境、数据路径），这是下游与上游的**有意分叉**，改动脚本逻辑时两边同步。

> **本 skill 存在的原因（真实事故）**：2026-10-27/28 门控全量标注（`label_gate_native.py --tiles 3`）
> 在 16 人共用的 pet 上运行时，主机 **load average 冲到 103**、**frp 隧道两度中断**（SSH 从 banner 超时
> 到 `Connection refused`，最长 >10 分钟）。当时的脚本没有任何预检与上限——因为项目里只有
> 「跑前 nvidia-smi 看一眼」的人工纪律。**从那次起，共享机上的重活必须走本 skill 的三道闸。**

## 1. 环境契约

| 项 | 值 |
|---|---|
| SSH | `ssh pet`（`~/.ssh/config` 里定义 Host/Port/User；**不要**在脚本里写死 IP） |
| 工作目录 | `/home/wyy/pet-action-recognition`（`git push pet main` 会同步到该 checkout） |
| Python 环境 | conda `plf`（`~/miniconda3/envs/plf`）；YOLO 相关用 `yolo` 环境 |
| GPU | 2× RTX 4090（24 GB/卡），**多人共享** |
| 数据 | `~/pet-final/datasets/cat_raw`（猫语料）、`~/mnt/dxm/dataset_*`（79 段事件片段）、NAS `~/mnt/` |
| 产物 | `results/<topic>/`（仓库内，gitignore） |

**代码只能经 git 流动**：本地 commit → `git push pet main` → 远端校验 `git log -1` 与 `git status`。
禁止 rsync/scp 覆盖远端 tracked 文件；一次性脚本放远端 `tmp/`（gitignored）。

**连 pet 不许走代理**：本机有全局代理时，`ssh`/`nc` 对 frp 隧道会表现为「超时/refused」。
脚本里已 `export NO_PROXY='*'` 并清空 `*_proxy`；手工连接前也请确认。

## 2. 三道闸

```bash
SD=.claude/skills/remote-ops/scripts

# ① 容量预检（跑任何东西之前）：GPU 是否有人真占显存、load/core、可用内存、磁盘
bash $SD/preflight.sh --gpu-index 0        # 在本地发起、在 pet 上执行（推荐）
bash $SD/preflight.sh --gpu-index 0 --json results/gate/preflight.json   # 顺带落盘证据

# ② 跑任何超过几秒的命令：包在守卫里（nice + 线程上限 + 看门狗）
bash $SD/remote_run.sh --gpu-index 0 --max-cpu-pct 350 --max-rss-mb 24000 --timeout-s 3600 \
  -- python3 scripts/label_gate_native.py --manifest ... --device cuda:0

# ③ 跑之前审代码：静态扫描 + 降规模冒烟（峰值 RSS 外推）
python3 $SD/code_audit.py audit scripts/label_gate_native.py
python3 $SD/code_audit.py smoke --cap-mb 2000 -- python3 scripts/<x>.py --limit {n}
```

### 退出码表（照此处置，不许绕过）

| 码 | 含义 | 处置 |
|---|---|---|
| 0 | 通过 | 开跑 |
| 1 | 硬阻塞（连不上、环境缺失） | 修好再跑 |
| 2 | **容量被占**（GPU 有人占显存、load 高、内存/磁盘紧） | **停下来问用户，不许抢** |
| 3 | CPU/内存/磁盘压力 / 静态审计有 high 级发现 | 等或降规模；high 级发现先修 |
| 4 | 看门狗按上限终止了命令 | 看采样日志定位哪个上限；降规模或调参后重跑 |
| 5 | 命令自己失败 | 修代码 |

**判 GPU 忙不忙看「有没有进程实际占着显存」（≥500 MiB 即判忙），不看瞬时利用率**——训练任务可能在
20% util 下握着 8 GB，采样窗口也可能正好落在 0%。

### 守卫默认上限（`resource_guard.sh run`）

| 项 | 默认 | 说明 |
|---|---|---|
| `--max-cpu-pct` | 350 | 进程树 CPU 上限（16 核机器上约 22%） |
| `--max-rss-mb` | 24000 | 进程树内存上限 |
| `--max-gpu-mem-pct` | 90 | 单卡显存占比上限 |
| `--timeout-s` | 3600 | 墙钟上限 |
| `--threads` | 8 | `OMP/MKL/OPENBLAS/NUMEXPR_NUM_THREADS` 上限 |
| `--nice` | 10 | 降权运行 |

采样间隔 5 s，写入 `.run/guard/run-<ts>.log`（远端工作目录下）。

## 3. 本仓的补充约定

- **数据/标注类长任务**（4K HEVC 逐帧解码 + 大模型前向）还要额外传 `--max-cpu-pct 250`，
  因为解码线程最容易把 load 顶起来。
- **严禁**在单次 `ssh 'cmd'` 里用 `nohup ... & disown` 启动后台任务——会话关闭会把它杀掉
  （真实事故：dog 复核跑到 2200/2661 被杀）。要么用远端 `setsid nohup ... &`，要么用
  `remote_run.sh`（推荐，带守卫与日志）。
- 长任务必须有日志文件 + 进度打印（每 25–200 条一次），否则无法判断它是在跑还是卡住。
- 收工前核对：GPU 显存回到基线、没有残留 python 进程（`ps aux | grep <script> | grep -v grep`）。

## 4. 与其他 skill 的分工

| 事项 | 去哪 |
|---|---|
| 怎么连、怎么预检、怎么守、怎么部署 | **本 skill** |
| 实验方法论（假设/对照/留痕/evidence.md） | `experiment` |
| 训练/测试/speedrun 的操作步骤 | `training` / `testing` / `speedrun` |
| 数据集与权重位置 | `datasets` |
| 远程仓库纪律（只读、git 交付） | `remote-server-discipline` |
