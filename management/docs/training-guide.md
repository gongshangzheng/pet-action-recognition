---
title: 训练体系
author: 郑鑫裕
date: 2026-09-16
tags: [训练, mmaction2, registry, 四种模式, checkpoint, 远程]
summary: mmaction2 训练机制 + 四种训练模式 + 模型 registry + configs/hooks + checkpoint 管理 + 远程执行闭环
id: 4
---

# 训练体系

> **怎么看**：§1 mmaction2 机制速览；§2 四种训练模式（互斥选一种）；§3 registry 与触发；§4 configs 与 hooks；§5 checkpoint 管理；§6 远程执行闭环（核心纪律）；§7 历史决策回顾。

## §1 mmaction2 机制速览

mmaction2 是 OpenMMLab 出品的**视频动作识别（video classification）框架**，继承 PyTorch。

- **vendored 快照**：`models/mmaction2/` 是 vendored 版本，**只读**，不直接改源码；定制走 config
- **config 继承**：用 `_base_=['./xxx.py']` 把多个 config 拼起来（数据集 / 模型 / 训练策略 / hooks 各自分文件）
- **训练入口**：`tools/train.py ${CONFIG} --work-dir ${WORK_DIR}`
- **数据流**：RawframeDataset / VideoDataset 加载视频 → pipeline 抽帧/缩放/增强 → 模型前向 → loss

**为什么不用 mmcv 改动**：GroundingDINO/HQSAM/ViTPose 依赖重且与 mmcv 约束冲突风险高（[6 号 §5.1](../wiki/architecture) D5），所以 pet 上另起 conda env `plf`，管线脚本以 subprocess + env 切换调用，产物落盘交接。

## §2 四种训练模式（互斥）

| 模式 | 何时用 | 触发方式 |
|---|---|---|
| **从头训练（from scratch）** | 全新数据集 / 新模型族首次尝试 | 不带 `--cfg-options load_from=...` 或 `resume_from=...` |
| **预训练微调（finetune）** | 拿预训练权重当起点 | `load_from=<pretrained.pth>` |
| **加载已有 checkpoint 继续训练** | 复现 / 调试 / 评估某个 ckpt | `load_from=<checkpoint.pth>` |
| **断点续训（resume）** | 上次训练中断/想接着跑 | `resume_from=<latest.pth>` |

**互斥关系**：同一时刻只能选一种——同时传 `load_from` 和 `resume_from` 会冲突。

**本仓库当前默认**：`--mode finetune`（带预训练权重）。从头训练仅用于完全不同的数据集/任务场景。

## §3 registry 与触发

### §3.1 模型 registry（21 分类 + 5 AVA 检测）

26 个模型（详 [3 号《模型》§5](../wiki/models)）注册在 `web/src/api/training.js` 后端：

- 训练 API：`POST /api/training/run`（前端训练表单）
- 测试 API：`POST /api/training/test`
- 路径：`web/src/views/training/{TrainConfig,TrainDataset,TrainModel,TrainRun,TrainResults,RunDetail}Manage*.vue`

### §3.2 触发方式

- **API**：前端表单 → 后端路由 → `scripts/train_model.py` → 远程 pet 执行
- **CLI 直跑**：`python scripts/train_model.py --model <id> --dataset <id> --work-dir <path>`

## §4 configs 与 hooks

### §4.1 configs/ 目录

| 文件 | 用途 |
|---|---|
| `configs/cats_videomaev2_base_16x4.py` | cats v1 + videomaev2-base 训练配置 |
| `configs/pet_mammal_aim_vitb_16x4.py` | mammal_v0 + AIM ViT-B |
| `configs/pet_mammal_posec3d_slowonly_quadruped.py` | quadruped + PoseC3D |
| `configs/pet_mammal_tsn_r50_256px.py` | TSN R50 256px 输入 |
| `configs/pet_mammal_uniformerv2_base_8x8.py` | UniFormerV2 |
| `configs/pet_mammal_videomae_base_16x4.py` | VideoMAE base |
| `configs/pet_mammal_videomae_v1_base_16x4.py` | VideoMAE v1 |
| `configs/pet_mammal_videomaev2_base_16x4.py` | VideoMAE v2 |
| `configs/quadruped_tsn_r50.py` | quadruped + TSN R50 |
| `configs/hooks/` + `configs/aim_modules/` | 自定义 hooks（共 14 文件含子目录） | 

### §4.2 自定义 hooks

`configs/hooks/` 下的自定义 hook 负责：

- 周期性评估（EvalHook）
- checkpoint 清理（只保留 best N 个）
- 学习率 warmup
- 日志格式

## §5 checkpoint 管理

### §5.1 下载预训练权重

- 单个：`python scripts/download_checkpoint.py --model <id>`
- 全部：`python scripts/download_checkpoint.py --all`

下载位置：

- 🖥️ pet：`~/pet-action-recognition/checkpoints/<model_id>/<model_id>_pretrained.pth`
- 速度 run 实验中已引用过：`/home/wyy/pet-action-recognition/checkpoints/tsn-resnet50/tsn-resnet50_pretrained.pth`

### §5.2 训练 checkpoint

输出到 `--work-dir` 指定路径（默认 `results/training/work_dirs/`）：

- `epoch_N.pth`：第 N epoch 的权重
- `latest.pth`：最近的（用于断点续训）
- `best_*.pth`：评估指标最佳的

## §6 远程执行闭环（核心纪律）

> 这一节是项目的硬性工作纪律。**远程服务器只用来执行，不要在那里开发或修改代码**。

### §6.1 闭环

```
本地写代码 → git commit → git push
       ↓
ssh pet
       ↓
git pull
       ↓
conda activate mmaction2
       ↓
python scripts/train_model.py ... 或 bash start_services.sh
       ↓
输出落到 pet 的 results/ 或 checkpoints/
       ↓
git add results/<specific_files> && git commit && git push
       ↓
本地 git pull 看结果
```

**绝对禁止**：远程编辑代码、装新依赖、改远程配置——这些都在本地完成。

### §6.2 后台启动纪律（macOS / Linux）

```bash
nohup cmd </dev/null > /tmp/log 2>&1 & disown
```

**`</dev/null>` 必填**——macOS nohup 进程不重定向 stdin 会挂起（即使是输出已重定向）。漏掉会让 ssh 会话超时。

### §6.3 进程检查防自匹配

`pgrep -f <关键词>` 会匹配到检查命令自身导致误报 RUNNING。**用日志标志**（如 `BATCH DONE`）、完整路径匹配、或 `ps aux | grep keyword | grep -v grep`。

### §6.4 GPU 共享

pet 是 2× RTX 4090，多用户共享：

- 训练前 `nvidia-smi` 看显存占用
- 不要一次性占满两卡——给其他人留空间
- 显存不够的模型（V-JEPA 2 等）走 bf16 + 梯度检查点（详 `video-feature-latent` 1.13）

### §6.5 脚本先进仓库

任何新脚本先 `git add scripts/<name>.py && commit`，再在远程用。**禁止在 `/tmp` 放脚本**——历史多次返工（multi_detect / kp_video / compare_mc）。

## §7 历史决策回顾（2026-07-13 计划吸收）

`docs/plans/2026-07-13-mmaction2-training-integration-plan.md` 的关键决策（已全部落地）：

1. **registry 从 `默认.py 抽出到独立模块`**：避免 26 个模型全堆在 default.py 里
2. **19→21 族注册**：新增 pets_mammal 系列配置（mammal_v0 专用）
3. **数据集类别注入**：避免硬编码——通过 `classes.txt` 动态注入
4. **四足 loader 骨架**：先建骨架（`datasets/quadruped_action/`），数据到位时填充

> 2026-07-13 计划已落地，本文件吸收后该文档 `git rm`。

---

**相关文档**：[3 号《模型》](../wiki/models)（每个模型实测）/ [2 号《数据集全景》](../wiki/datasets)（喂什么数据）/ [6 号《系统架构》§5.1](../wiki/architecture)（环境隔离）/ `.claude/skills/remote-servers/`（远程服务器）/ `.claude/skills/training/`（训练操作指南）