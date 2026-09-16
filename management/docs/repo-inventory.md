---
title: 仓库资产盘点
author: 郑鑫裕
date: 2026-09-16
tags: [资产, 盘点, 索引, wiki]
summary: 全库唯一入口——有什么重要内容/数据、在哪、什么状态
id: 1
---

# 仓库资产盘点

> **盘点基准日 2026-09-16**。读这份文档五分钟，把仓库装进脑子里。
>
> **位置图例**：🗄️ = 仓库内 ｜ 🖥️ = pet 远程（仅读执行环境，不要直接改） ｜ 💽 = NAS（共享存储）

## 导航：本套 wiki 共 11 篇

| # | 篇名 | 一句话 |
|---|---|---|
| 1 | 仓库资产盘点（你正在读） | 全库唯一入口 |
| 2 | [数据集全景](../wiki/datasets) | 所有数据集：规模/标注/位置/状态 |
| 3 | [模型](../wiki/models) | 我们测过的模型 + 实测结果 |
| 4 | [训练体系](../wiki/training-guide) | 怎么训：mmaction2 + 四种模式 |
| 5 | [Live 模块](../wiki/live-module) | 直播源管理 + 实时推理 |
| 6 | [系统架构](../wiki/architecture) | 完整结构总览 + 进度计划 |
| 7 | [身份标识与检索](../wiki/identity-and-retrieval) | 定位追踪+猫 Re-ID+RAG 式物体标识 |
| 8 | [身份-动作 Tokenizer 专篇](../wiki/identity-tokenizer) | FLOAT×TiTok 架构与两阶段路线 |
| 9 | [研究结论与踩坑](../wiki/lessons) | 关键点五大问题 + 标注体系教训 + 用户裁定时间线 |
| 10 | [第三方项目借鉴](../wiki/third-party-notes) | pet-videos / remix-petra 等借鉴与反模式 |
| 11 | [交接与协作指南](../wiki/handover-guide) | 新协作者上手入口 |

## §1 数据资产

| 资产 | 路径/位置 | 规模 | 状态 | 用途 |
|---|---|---|---|---|
| cats v1 家猫监控（双人标注·中英双名） | 🗄️ `datasets/cats/` | 552MB（8 zip，实际 4 个唯一文件） | **已就绪**（每份文件中文 + 拼音双名） | 训练/评测/猫语料迁移 |
| cats zip 清单 | 🗄️ `datasets/cats/` | dataset_蒋(159M) / dataset_崔(117M) / dataset_cui(159M) + 三个 annotation_*.zip(32–84K) | — | 视频原始数据 + 标注 |
| quadruped_action 占位 | 🗄️ `datasets/quadruped_action/` | 骨架（classes.txt + 3 个 ann list，无视频） | **占位** | mmaction2 训练目标 |
| mammal_v0 | （路径待补，建议 `datasets/mammal_v0/`） | 七类 ~3h | 在用 | 迁移基线、V-JEPA 1.13 对照 |
| UCF101 | 💽 NAS（路径见 `remote-servers` skill） | 13320 段 / 101 类 | 外部 | 身份-动作 Tokenizer 阶段 A 验证 |
| 34 段白天事件片段 | 🖥️ pet `~/results/batch/`（原始）+ 🗄️ `results/batch/`（本地副本） | 14.7 分钟语料（短事件片段） | 已处理 | 管线验证 + 演示 |
| kinetics400 | （路径待补） | 仅 k400 烟测 | — | k400-smoke-tsn top1=0.77 |
| 论文库 papers.db | 🗄️ `data/papers.db` | 239 篇 / 519 类目 | 在写入 | 论文检索与筛选 |
| 论文 SQLite 备份 | 🗄️ `data/papers.db.bak-seed` | 32KB | 8-31 种子备份 | 现库健康（integrity_check ok） |
| 论文源数据 | 🗄️ `data/extracted_papers.json` | 140 篇（博客 17 篇提取源） | — | 论文导入入口 |
| frontier 论文调研 | 🗄️ `data/researched_papers.json` | 72 篇 | — | frontier 动作识别研究 |
| livestock/身份论文调研 | 🗄️ `data/researched_papers_identity.json` | 20 篇 | — | 数字人 motion-latent + livestock |
| Live SQLite | 🗄️ `results/live/live.db` | 1 stream_source / 1 screenshot | 在用 | Live 模块数据 |
| 🖥️ pet checkpoints | `~/pet-action-recognition/checkpoints/<model>/<model>_pretrained.pth` | 各模型预训练权重 | 已知路径 | 训练/推理加载 |

## §2 产物资产

| 子目录 | 内容 | 关键数字 | 来源 |
|---|---|---|---|
| `results/training/` | 5 个训练 run + k400 烟测 + work_dirs + logs | **5 run 全部 error**（数据/接口问题）；k400-smoke-tsn top1 0.77 / top5 0.925 / latency 278.8ms / RTF 0.032 | `train_model.py`、`run_test.py` |
| `results/speedrun/` | speedrun 评测结果 | 366 条 / 24 模型（generated 2026-08-15） | `speedrun.py` |
| `results/batch/` | 34 段白天视频批处理 | 检出率 0.939 / 插值率 0.905 / 校正率 0.334；3 告警段已结案（2026-09-15） | `pet_detect_track.py`、`make_followcam.py` |
| `results/batch/alarm/` | 低检出率段接触表 | 3 张 jpg | 同上 |
| `results/gate0a/` | 第一阶段多目标检测门验收（contact sheet + followcam + side_by_side） | 1 套 | `pet_multi_detect.py` |
| `results/gate0a_v2/` `gate0a_v3/` | 多目标检测门迭代产物 | mp4 + jpg | 同上 |
| `results/gate0b/` | 关键点提取门（HRNet vs ResNet-101 对比） | 2 段 × 2 模型 = 4 个 mp4/jpg | `extract_keypoints_from_tracks.py` |
| `results/gate4/` | 跟踪门（multi_detect v1/v2） | mp4 | `pet_multi_detect.py` |
| `results/skeleton/` | 关键点可视化 | ap10k_vis（HRNet）+ dlc_vis（SuperAnimal） | 同上 |
| `results/live/` | Live SQLite | live.db | `live_analyze.py` / `live_stream.py` |

## §3 代码模块

| 层 | 数量 | 入口 |
|---|---|---|
| Server 后端 | 7 个 FastAPI 路由 | `server/main.py` → `server/routers/{papers,management,evaluation,training,speedrun,datasets,live}.py` |
| Scripts | 26 个 Python + Shell | `scripts/`（按用途分组） |
| petlib | 4 个模块 | `petlib/{registry,schemas,videowriter,contract_tests}.py` |
| Web 前端 | 28 个 .vue 页面 + 8 个 API 封装 | `web/src/{views,api}/` |
| Configs | 14 个（含 hooks/aim_modules 子目录） | `configs/` |
| Vendored | `models/mmaction2/` | vendored 快照，只读 |

scripts 按用途分组：

- **训练**：`train_model.py`、`train_all_models.py`、`assert_aim_frozen.py`
- **测试/烟测**：`run_test.py`、`eval_all_k400.py`、`benchmark_speed.py`
- **推理（单视频）**：`inference.py`、`_infer.py`、`vlm_infer.py`、`run_test_vlm.py`
- **Speed Run**：`speedrun.py`
- **批处理/对比**：`pet_batch_run.py`、`pet_detect_track.py`、`make_followcam.py`、`pet_compare_followcam3.py`、`pet_compare_track_correction.py`、`pet_multi_detect.py`、`pet_seg_contact.py`、`rtmdet_cross_check.py`、`yolo11_zeroshot_audit.py`
- **关键点**：`extract_keypoints_from_tracks.py`、`keypoint_mapping_quadruped.json`
- **Live**：`live_analyze.py`、`live_stream.py`
- **工具**：`md_to_docx.sh`、`pet_repin.sh`

## §4 论文模块

- DB：`data/papers.db` 239 篇 / `paper_categories` 519 条（详见 [2 号《数据集全景》](../wiki/datasets) §8 标注类目规范）
- 三类研究 JSON：
  - `extracted_papers.json`：博客 17 篇提取源 → 140 条
  - `researched_papers.json`：frontier 动作识别 → 72 条
  - `researched_papers_identity.json`：livestock/身份/数字人 motion latent → 20 条

## §5 项目管理数据（`management/`）

| 子目录 | 文件数 | 用途 |
|---|---|---|
| `team/` | 3 | 团队成员档案 |
| `daily/` | 3 | 日报 |
| `weekly/` | 10 | 周报 |
| `monthly/` | 3 | 月报 |
| `meetings/` | 2 | 会议纪要 |
| `projects/` | 27 | 项目树 + tasks.json（任务看板实时数据） |
| `docs/` | 整合后 11 篇新文档 | 本套 wiki |

> ⚠️ 整合前 wiki 9 篇 → 删除 8 篇被吸收的 + `tasks.md`（已过时）→ 本套 11 篇接替。

## §6 openspec change 全景

> 8 活跃 + 16 归档。一句话定位、进度、状态；详情见 [6 号《系统架构》§8](../wiki/architecture) 与 [1 号 §7 外部资产索引](#7-外部资产索引)。

### 6.1 活跃 change（8 个）

| Change | 一句话 | 进度 | 状态 |
|---|---|---|---|
| `pet-motion-latent-pipeline` | **总管**——管线全景+主线/旁支总览 | 5/11 任务 | 主线 |
| `batch-followcam-extraction` | 34 段白天批处理（多 prompt 检测+运动校正+跟随视频） | 5/6 | 待归档 |
| `video-feature-latent` | 行为表征学习（窗口特征+UMAP+HDBSCAN+CatHuBERT） | 1/14 | 主线 |
| `identity-action-tokenizer` | FLOAT×TiTok 杂交，UCF101→猫两阶段 | 0/9 | 研究型 |
| `spot-check-cli` | 抽查报告 CLI | 0/4 | 主线（待前置） |
| `registry-retrieval` | 统一登记-检索（猫 Re-ID + 物体实例） | 0/4 | 条件启动（用户批准触发） |
| `tracker-selection` | 多猫场景下的跟踪器选型 | 0/4 | 条件启动（多猫数据出现触发） |
| `behavior-anomaly-detection` | 行为异常检测（token/簇机制） | 0/5 | 研究型（前置归档触发） |

### 6.2 归档 change（16 个）

一行表见 `openspec/changes/archive/` 列表（已被实施并归档）。包括但不限于：

- `2026-08-15-speedrun-*`、`2026-08-16-add-md-to-docx`、`2026-09-10-cats-videomaev2-finetune`、`2026-09-10-docs-animal-action-survey`、`2026-09-10-integrate-frontier-models`、`2026-09-10-provision-a100-server-superseded`、`2026-09-10-yolo11-detection-prep`、`2026-09-15-cats-dataset-v1`、`2026-09-15-cats-speedrun`、`2026-09-15-fix-train-override-mvit-x3d-uniformer`、`2026-09-15-fix-training-api-device-pretrained`、`2026-09-15-multi-object-detect-gate`、`2026-09-15-seed-papers-library` 等

## §7 外部资产索引

| 来源 | 名称 | 状态 | 详情 |
|---|---|---|---|
| 🖥️ pet | `~/pet-action-recognition/` | 远程开发机（2× RTX 4090） | 所有训练/批处理在此跑；详见 `.claude/skills/remote-servers/` |
| 💽 NAS | UCF101 / 大语料 | 共享磁盘 | 挂在 pet 上；具体路径见 `remote-servers` skill |
| 🗄️ `third-party/` | kabr-tools / keypoint-moseq / pet-videos / PigDetect / remix-petra | 5 个第三方库 | 详 [10 号《第三方项目借鉴》](../wiki/third-party-notes) |
| `.claude/skills/` | 15 个 agent skill | 仓库内随版本管理 | 操作指南（agent 用） |
| `.pi/skills/` | OpenSpec skills（propose / apply / archive / explore / sync / update） | OpenSpec 工作流 | 提案 / 实施 / 归档 / 探索 / 同步 / 更新 |

## 附录 A：顶层散落文件清单（待清理项）

由独立 change `chore-toplevel-cleanup` 处理（已另立 change）：

- 5 个误拷冗余副本（CanvasPlayer.vue / Live.vue / live.py / live_stream.py / config.py / package-lock.json）— git rm
- 2 项需用户确认后删：remix_-派爪petra.zip / papers.db.bak-seed
- pet-videos.zip **内容与 `third-party/pet-videos/` 不一致**（zip 含 `.git`+`__MACOSX`），默认保留待裁定
- 保留：`.playwright-mcp/`（已 ignore，MCP 工具使用中）、空目录 `checkpoints/`
- 散落 `.DS_Store`：本地 find -delete（不入 commit）

## 附录 B：空 / 失效目录

- `checkpoints/`（本地空目录，权重实际在远程 pet 服务器）
- `evaluation/{datasets,models,configs,scripts,outputs}/`（空目录占位，待启用）