---
title: 模型
author: 郑鑫裕
date: 2026-09-16
tags: [模型, mmaction2, 关键点, 检测, 实测, 注册库]
summary: 重要模型逐个条目（简介 + 实测结果）；含分类/关键点/检测三大类，registry 其余未实测项明确标注
id: 3
---

# 模型

> **怎么看**：每个模型一个固定两段式条目——**简介**（架构与定位一句话） + **实测结果**（数字+状态+证据路径）。我们实际训练/测试/使用过的都详写；registry 里的其余模型速览表只标名字+用途，**明确标注"未实测"**。

## §1 重要模型总览

| 类型 | 模型 | 状态 | 一句话定位 |
|---|---|---|---|
| 分类 | videomaev2-base | 已实测（×2 run，**error**） | 当前最强自监督预训练家族 |
| 分类 | slowonly-resnet50 | 已实测（error） | 经典 3D CNN，slow path |
| 分类 | tsm-resnet50 | 已实测（error） | 2D CNN + 时序位移，性价比 |
| 分类 | timesformer-divst | 已实测（error） | 时空分离注意力 |
| 分类 | tsn-resnet50 | 已实测（k400 烟测 + speedrun） | 2D CNN 基线，验证管线用 |
| 关键点 | HRNet | 已实测（AP-10K） | 高分辨率关键点 |
| 关键点 | ResNet-101 | 已实测（AP-10K） | 经典 2D 关键点 |
| 关键点 | SuperAnimal | 已对比（视频） | 跨物种通用 |
| 检测 | GroundingDINO | 已实测 | 开放词汇（碗/摄像头被裁定撤下） |
| 检测 | YOLO11 | 已实测（zeroshot audit） | RTMDet 实时检测对照 |
| 检测 | OWLv2 | 已实测 | 开放词汇对照 |

> Registry 其余 15 个模型未实测，速览见 §5。

---

## §2 分类模型

### §2.1 videomaev2-base

**简介**：VideoMAE v2 基础版，基于 masked autoencoding 自监督预训练的视频 Transformer，是当前 mmaction2 注册模型里最强的自监督代表。架构：ViT-B + 时空联合。

**实测结果**：
- 2 个训练 run（`results/training/metrics.json`）
  - `train-videomaev2-base-quadruped_cats_v1-1786596935`
  - `train-videomaev2-base-quadruped_cats_v1-1786596987`
- 数据集：`quadruped_cats_v1`
- 状态：**两次均 error**
- 超参：epochs=15 / lr=1e-4 / batch_size=4 / device=cuda
- **结论/教训**：error 集中在数据/接口层面，不是模型本身的问题。需要排查 mmaction2 对 cats v1 ann_file 的兼容性。

### §2.2 slowonly-resnet50

**简介**：SlowOnly 是 3D CNN 的精简版本——只保留"慢速路径"（低帧率、强空间特征），去掉快速路径。在 Kinetics 系列上是经典 baseline。

**实测结果**：
- 1 个 run（`train-slowonly-resnet50-quadruped_cats_v1-1786596942`）
- 状态：**error**
- 结论：与 videomaev2 同根问题（数据/接口）

### §2.3 tsm-resnet50

**简介**：TSM（Temporal Shift Module）——把 2D ResNet 加上时序位移操作获得时序建模能力，性价比高。

**实测结果**：
- 1 个 run（`train-tsm-resnet50-quadruped_cats_v1-1786596939`）
- 状态：**error**

### §2.4 timesformer-divst

**简介**：TimeSpler 的"时空分离注意力"变体（Divided Space-Time），先算空间、再算时序，节省显存。

**实测结果**：
- 1 个 run（`train-timesformer-divst-quadruped_cats_v1-1786596945`）
- 状态：**error**

### §2.5 tsn-resnet50

**简介**：TSN（Temporal Segment Network）——最经典的 2D CNN 基线，把视频分成 K 段、每段取一帧用 2D ResNet 提特征再融合。验证管线用。

**实测结果**：
- **k400 烟测**（`results/training/test_results.json`）全套指标：

  | 指标 | 数值 | 意义 |
  |---|---|---|
  | top1_acc | **0.77** | 第一类准确率 77% |
  | top5_acc | **0.925** | 前五类准确率 92.5% |
  | mean1_acc | 0.6712 | 类别平均准确率（67.12%） |
  | latency_ms | 278.8 | 单样本推断耗时 278.8ms |
  | fps | 3.59 | 每秒推断 3.59 个 clip |
  | RTF | 0.032 | 推断速度是实时的 ~30 倍 |
  | GPU 显存 | 3068.5 MB | 单卡 3GB 占用 |
  | 参数量 | 24.33 M | 2400 万参数 |
  | ckpt 大小 | 97.6 MB | checkpoint 文件 97.6MB |
- **Speed Run**：366 条结果覆盖 24 个模型（`results/speedrun/results.json`，generated 2026-08-15），tsn-resnet50 在其中。Speed Run 用法见 `speedrun.py` 和 `.claude/skills/speedrun/`。

## §3 关键点模型

### §3.1 HRNet（AP-10K）

**简介**：高分辨率关键点网络——保持高分辨率表征贯穿全程，多分辨率子网并行交换信息。在人体姿态估计上经典，迁移到动物（AP-10K 数据集）。

**实测结果**：
- 数据集：AP-10K
- 对照位置：`results/gate0b/074451_hrnet.jpg` / `074451_kp.mp4` / `120311_hrnet.jpg`
- **关键裁定**：MC 跟随视角实测 ——
  - mean_conf **0.367**
  - conf > 0.5 帧仅 **0.2%**
  - 四肢点 < 0.25
- **结论（2026-09-15 用户裁定）**：**关键点整体移出管线**。MC 视角下置信度太差，无法支撑下游任务。批处理不产出 NPZ。脚本 `scripts/extract_keypoints_from_tracks.py` 保留入库备查。

### §3.2 ResNet-101（AP-10K）

**简介**：经典 2D ResNet-101，AP-10K 上作为 baseline 对照。

**实测结果**：
- 对照位置：`results/gate0b/074451_res101.jpg`
- 结论：与 HRNet 同——置信度太低，移出管线

### §3.3 SuperAnimal

**简介**：跨物种通用关键点模型（DeepLabCut 出品），单模型覆盖多种四足动物。

**实测结果**：
- 对比视频：`results/skeleton/dlc_vis/*.mp4`
- 结论：与 HRNet/ResNet-101 同——置信度不达标，移出管线

## §4 检测模型

### §4.1 GroundingDINO

**简介**：开放词汇检测器——给它文字提示（如"cat"），它就在图里框出对应的物体。pipeline 主力检测器。

**实测结果**：
- 34 段白天视频批处理（详 [2 号《数据集全景》§5](../wiki/datasets)）
  - **检出率 mean 0.939**（每 10 帧抽样中含猫帧占比）
  - 插值率 0.905 / 校正率 0.334
- **重要裁定（multi-object-detect-gate）**：
  - **碗**：100% 全误框（text 路线不通）
  - **摄像头**：召回 4/1859（千分之 2.2，不可用）
  - **猫**：表现良好（>90% 检出）
- **结论**：文字提示路线仅保留 "cat" / "person" / "litter_box" / "door_window" 等可用类；碗/摄像头改走 RAG 式（SAM 候选 + embedding 检索），详 [7 号《身份标识与检索》§4](../wiki/identity-and-retrieval)

### §4.2 YOLO11

**简介**：YOLO 系列最新实时检测器，RTMDet 同级别。

**实测结果**：
- 脚本：`scripts/yolo11_zeroshot_audit.py`
- 结论：作为 GroundingDINO 的对照验证（实时性更好但零样本检测能力不及 GroundingDINO）

### §4.3 OWLv2

**简介**：开放词汇检测器（与 GroundingDINO 同类思路），可文字提示也支持图像引导查询。

**实测结果**：
- 作为 GroundingDINO 碗/摄像头裁定的对照（图像引导 "拿这个碗的照片当查询"）
- 结论：详见 [7 号 §4.5](../wiki/identity-and-retrieval)——碗/摄像头裁定撤下 GDINO 文本路线

## §5 注册库其余模型速览（未实测）

> **未实测项明确标注**。下表是当前 mmaction2 注册的 26 个模型（21 分类 + 5 AVA 检测）的速览，**未经实测测试，仅作能力地图**。需要时再实测。

### §5.1 分类模型（21 个，5 个已实测见 §2）

| 模型族 | 输入 | 用途 | 实测 |
|---|---|---|---|
| videomaev2-base | 16×4 | 自监督 SOTA | ✓ (§2.1) |
| slowonly-resnet50 | 8×8 | 3D CNN | ✓ (§2.2) |
| tsm-resnet50 | 8×8 | 时序位移 | ✓ (§2.3) |
| timesformer-divst | 8×8 | 时空分离 | ✓ (§2.4) |
| tsn-resnet50 | 8×3 | 2D CNN 基线 | ✓ (§2.5) |
| uniformerv2-base | 8×8 | U-ViT | ✗ |
| posec3d-slowonly | — | 姿态 3D | ✗ |
| videomae-base | 16×4 | MAE 自监督 | ✗ |
| videomae-v1-base | 16×4 | MAE v1 | ✗ |
| aim-vitb | 16×4 | AIM 注意力 | ✗ |
| mvit-small | — | MViT | ✗ |
| x3d-xs | — | X3D tiny | ✗ |
| r50 | — | ImageNet 预训练 | ✗ |
| (其他 ~7 个) | — | mmaction2 默认注册 | ✗ |

### §5.2 AVA 检测模型（5 个）

| 模型 | 实测 |
|---|---|
| slowfast-ava | ✗ |
| (其他 4 个) | ✗ |

## §6 结论汇总表

按 D6 四要素（日期/来源/关键数字/证据路径）：

| 结论 | 日期 | 来源 | 关键数字 | 证据路径 |
|---|---|---|---|---|
| 5 个训练 run 全部 error | 2026-08-13 | `train_model.py` 全量实验 | error × 5 | `results/training/metrics.json` |
| k400 烟测管线可跑通 | 2026-08-23 | `run_test.py` k400-smoke-tsn | top1 0.77 / top5 0.925 | `results/training/test_results.json` |
| 关键点 MC 置信度过低 | 2026-09-15 | `extract_keypoints_from_tracks.py` + 用户裁定 | mean_conf 0.367 / > 0.5 帧 0.2% | `results/gate0b/` |
| 碗 GDINO 文本全误框 | 2026-09-15 | `multi-object-detect-gate` | 100% 误框 | `results/gate0a/` |
| 摄像头 GDINO 召回 4/1859 | 2026-09-15 | `multi-object-detect-gate` | 召回率 0.22% | `results/gate0a/` |
| 批处理 34/34 完成 | 2026-09-15 | `pet_detect_track.py` + `make_followcam.py` | 检出率 0.939 / 23 分钟 | `results/batch/batch_report.md` |
| 运动校正 v5 参数定稿 | 2026-09-15 | 三轮迭代 v1→v5 | 触发率 12.0% / 偏移 max 108px | `results/batch/` |
| Speed Run 24 模型 366 条 | 2026-08-15 | `speedrun.py` | 366 条 / 24 模型 | `results/speedrun/results.json` |

---

**相关文档**：[4 号《训练体系》](../wiki/training-guide)（训练机制与配置）/ [6 号《系统架构》](../wiki/architecture)（模型在管线中的位置）/ [7 号《身份标识与检索》](../wiki/identity-and-retrieval)（检测模型应用场景）