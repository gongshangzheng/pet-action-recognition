---
title: 数据集全景
author: 郑鑫裕
date: 2026-09-16
tags: [数据集, 标注, cats, UCF101, quadruped, label_map]
summary: 当前所有数据集——规模/标注/位置/状态/用途；含标注类目规范全文（吸收原 detection-annotation-taxonomy）
id: 2
---

# 数据集全景

> **怎么看**：先用 §1 总览表快速扫一遍；想深入哪个数据集跳到对应 §；§8 是标注规范原文；§9 是 label_map/ann_file 工程约定。

## §1 总览表

| 数据集 | 规模 | 类别数 | 标注情况 | 位置 | 状态 | 主要用途 |
|---|---|---|---|---|---|---|
| **cats v1** 家猫监控 | 552MB（8 zip，实际 4 个唯一文件） | 8 类检测 + 活动标注 | 双人标注（蒋 = jiang、崔 = cui），中文名 + 拼音名双份拷贝 | 🗄️ `datasets/cats/` | 在用 | 训练 + 评测 + 行为发现 |
| **pet_action_mammal_v0** 四足哺乳动物 | ~3 小时 | 7 类 | 已标注 | 建议 `datasets/mammal_v0/` | 在用 | 迁移基线、V-JEPA 1.13 对照 |
| **UCF101** 人类动作 | 13320 段 / 101 类 | 101 | 已标注 | 💽 NAS | 外部 | 身份-动作 Tokenizer 阶段 A 验证 |
| **34 段白天事件片段** | 14.7 分钟 | — | 无类别（用作管线验证） | 🖥️ pet 原始 + 🗄️ `results/batch/` 副本 | 已处理 | 管线验证 + 演示 |
| **kinetics400** | 400 类 | 400 | 烟测用 | （路径待补） | 外部 | k400 烟测（top1=0.77） |
| **quadruped_action** 四足（占位） | 0 视频 |  | 骨架 + 3 个空 ann list | 🗄️ `datasets/quadruped_action/` | 占位 | mmaction2 训练目标 |

## §2 cats v1（家猫监控）

### §2.1 来源与结构

**双人标注**——两个标注者（蒋/崔）独立标注同一批视频，**每位标注者对应一个视频包 + 一个标注包**；项目同时保留**中文名 + 拼音名**两份拷贝（sha256 一致，仅文件名不同；中英双名便于跨工具兼容）：

```
datasets/cats/
├── dataset_蒋.zip     159M    视频数据（蒋命名）        ╮
├── dataset_jiang.zip  159M    视频数据（蒋拼音）       ╯ 同一份文件
├── dataset_崔.zip     117M    视频数据（崔命名）        ╮
├── dataset_cui.zip    117M    视频数据（崔拼音）       ╯ 同一份文件
├── annotation_蒋.zip   84K    标注（蒋命名）           ╮
├── annotation_jiang.zip 84K   标注（蒋拼音）          ╯ 同一份文件
├── annotation_崔.zip   32K    标注（崔命名）           ╮
└── annotation_cui.zip  32K    标注（崔拼音）          ╯ 同一份文件
```

> 上表大小为 2026-09-16 状态；实际唯一文件 4 个：dataset_蒋（=jiang）、dataset_崔（=cui）、annotation_蒋（=jiang）、annotation_崔（=cui）。拼音名是 8-12 批量重命名/重打包的产物，mtime 一致（20:41）。

总时长约 3 小时，包含 8 类检测（详 §8）+ 活动标注。

### §2.2 标注质量问题：activity 伞类

**重要事实**：人工标注的 activity 类目里"伞类"占了**一半以上**——意思是人也不知道猫到底分几类活动，多个不同动作被打成同一个大类。

**后果**：不能直接拿这套人工 5 类表作为训练目标——模型会学到"伞类"这个伪类别而不是真正的行为差异。

**应对**：项目主推"无监督发现行为"路线（`video-feature-latent`）：让数据自己聚成簇，再人工命名。这正是 identity-action-tokenizer change 想用 FLOAT×TiTok 杂交架构解耦的原因。

### §2.3 训练目标

cats v1 主要用作：

- mmaction2 注册模型微调（5 个训练 run 全部 error——数据/接口问题）
- 身份-动作 Tokenizer 阶段 B 迁移
- spot-check-cli 抽查报告的 ground-truth 来源

## §3 pet_action_mammal_v0（四足哺乳动物）

### §3.1 来源与规模

约 3 小时，**七类**。来源（MammalNet 衍生 / 自建待确认）。

### §3.2 label_map 与用途

- `label_map` 位置建议：`datasets/mammal_v0/classes.txt`
- 用途：
  - **迁移基线**：从人（UCF101）/ 通用四足跨到宠物猫
  - **V-JEPA 2 fpc16 微调对照**（`video-feature-latent` 1.13）

### §3.3 与 cats v1 的关系

mammal_v0 与 cats v1 的关系是"通用四足 → 宠物猫"。两者共享行为语义（吃/喝/睡/走等），但标注质量不同——mammal_v0 标注更规整，cats v1 标注有"伞类"问题。**主语料以 cats v1 为主，mammal_v0 作对照/补强**。

## §4 UCF101（人类动作）

### §4.1 来源与规模

- 💽 NAS 共享磁盘
- 13320 段 / 101 类
- 路径：见 `.claude/skills/remote-servers/` 文档

### §4.2 用途：身份-动作 Tokenizer 阶段 A 验证

猫语料太少（34 段 = 14.7 分钟 + 3k clips），训不动视频生成模型。**解法**：先在 UCF101（13320 段，规模大两个数量级）验证"FLOAT×TiTok 杂交架构"可行性，再迁移到猫语料。

UCF101 上的"身份" = "这是哪个人"，与猫 Re-ID 同构。

## §5 34 段白天事件片段

### §5.1 语料事实修正

> **重要**：34 段不是 34 段完整录像，而是 **34 段短事件片段，总素材仅 14.7 分钟**（2026-09-15 修正）。

来源：家猫监控原始视频 → event 边界检测 → 截取的 34 个短事件。每个片段约 25 秒，加起来不到 15 分钟。

### §5.2 批处理结果

`scripts/pet_detect_track.py` + `scripts/make_followcam.py` 处理后（2026-09-15 完成）：

- 成功率：**34/34**
- 总耗时：23 分钟
- 检出率：mean 0.939（每 10 帧抽样中含猫帧占比）
- 插值率：mean 0.905（结构性 ≈90%，源于每 10 帧抽样设计，**非异常**）
- 运动校正触发率：mean 0.334

### §5.3 三个告警段结案

| 段 | 检出率 | 原因 | 处置 |
|---|---|---|---|
| `event_20260806_100505` | 0.227 | 15 秒超短片段 + 低猫在场率 + 红外域置信度边缘 | 保留原样，如实标注在场率 |
| `event_20260806_180330` | 0.304 | 同上 | 同上 |
| `event_20260806_094251` | 0.833 | 轻度偏低 | 无需特殊处理 |

**结案**：三告警段均为**短事件片段 + 低猫在场率 + 红外域边缘**，**非算法故障**。

### §5.4 角色定位

- 34 段跟随视频承担**管线验证 + 演示**角色
- **不是**训练主力——训练主语料是 cats v1（~3h）和 mammal_v0（~3h）
- 行为发现主依赖 mammal_v0 + cats v1 共 ~3 小时语料

## §6 kinetics400（仅烟测）

仅用作 k400 烟测：

- 测试 ID：`k400-smoke-tsn`
- 模型：`tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py`
- 结果：top1 0.77 / top5 0.925 / mean1 0.6712（详 [3 号《模型》](../wiki/models) §2）

不参与猫语料训练，只验证"mmaction2 + 训练 pipeline 能跑通"。

## §7 quadruped_action（四足占位）

### §7.1 期望结构（来自 `datasets/quadruped_action/README.md`）

```
datasets/quadruped_action/
├── classes.txt                       # 每行一个动作类别名
├── quadruped_action_train_list.txt   # 每行：videos_train/xxx.mp4 <label>
├── quadruped_action_val_list.txt     # 每行：videos_val/xxx.mp4 <label>
├── quadruped_action_test_list.txt    # 每行：videos_test/xxx.mp4 <label>
├── videos_train/
├── videos_val/
└── videos_test/
```

### §7.2 状态

**占位骨架**：classes.txt + 3 个 ann list 已就位，**无视频**。待数据到位时填充。

## §8 标注类目规范（全文迁入 detection-annotation-taxonomy）

> 以下全文来自 `management/docs/detection-annotation-taxonomy.md`，整合到本节。原文件在本 change 中被吸收删除。

### §8.1 概述

本节是项目检测任务的**标注类目全集 + 边界规则 + COCO 映射 + 中期验收映射**。训练检测器、抽查报告字段、跟踪器空间状态字段都依据本节。

### §8.2 类目全集（8 类）

| 类目 | 中文 | 用途 |
|---|---|---|
| cat | 猫 | 主目标 |
| person | 人 | 中期验收特征上报 |
| food_bowl | 食盆 | 物体实例识别（RAG） |
| water_bowl | 水盆 | 同上 |
| litter_box | 猫砂盆 | 同上 |
| toy | 玩具 | 物体实例识别 |
| door_window | 门窗 | 空间状态判断 |
| cat_face | 猫脸 | **新增类**——猫 Re-ID 用，区别于 cat（全身） |

### §8.3 各类标注边界规则

#### cat（猫）
- **框选范围**：头到尾，包括四肢完全入画的状态
- **截断**：猫部分在画面外，只标入画部分；四肢任一截断都视为截断状态
- **姿态**：站/坐/躺/跳均可；框选紧贴身体轮廓外延 +5px 留白
- **遮挡**：猫被物体（家具/门）遮住超过 50% 时，**不标**——避免引入遮挡伪样本
- **多只**：每只独立框，互相重叠时按 z-order（深度）先标前面的

#### person（人）
- 完整入画的人——头到脚可见
- **不算**：手/脚单独出现（不是 person）
- 中期验收特征上报字段，与"猫在场率"交叉校验

#### food_bowl / water_bowl（食盆/水盆）
- 实物盆体可见即可标
- 区分：盆内有食物/水的为对应类（food/water）
- 空盆也算对应类——按材质/位置判断，不按内容物
- 多个堆叠或并排：每个独立框

#### litter_box（猫砂盆）
- 猫砂盆本体的外延——包括有/无顶盖的样式
- 不标猫砂（盆内的内容物）

#### toy（玩具）
- 球类、逗猫棒、激光笔等可识别的小物体
- 玩具在猫嘴里也照样标（不因为被咬住就跳过）

#### door_window（门窗）
- 房间门、推拉门、窗户——可通行的开口
- 不标不可通行的装饰性门（如橱柜门）

#### cat_face（猫脸）——新增类
- **专门为猫 Re-ID 设立**：区别于 cat（全身）
- 框选范围：耳尖到下巴，左右脸颊外延
- 用于身份登记照的关键区域

### §8.4 COCO 预标注类映射

| COCO 类 | 项目类 | 备注 |
|---|---|---|
| cat | cat | 直接映射 |
| person | person | 直接映射 |
| bowl | food_bowl / water_bowl | 二分类需人工判断 |
| bed / couch | door_window | 误映射，需人工修正 |
| （无） | litter_box | 无 COCO 对应，纯人工标 |
| （无） | toy | 部分对应 sports ball |
| （无） | cat_face | 无 COCO 对应 |

### §8.5 中期验收特征上报映射

11 月中期验收的"宠物场景识别准确率"指标 = 抽查报告字段 + 标注类目交叉：

| 验收项 | 所需类目 | 数据来源 |
|---|---|---|
| 猫在场率 | cat + cat_face | spot-check-cli 报告 |
| 喂食/饮水事件 | food_bowl + water_bowl + 猫运动 | 抽查报告时间轴 |
| 排泄事件 | litter_box + 猫进出砂盆 | 抽查报告时间轴 |
| 多猫场景 | cat + cat 之间的 id 切换 | 跟踪器 + ID 检索 |

## §9 label_map / ann_file 约定

> 引用自 `.claude/skills/datasets/`。完整细节见该 skill。

### §9.1 per-model label_map

- 路径：`configs/<config>.py` 内部定义或 `data/<dataset>/classes.txt`
- 格式：每行一个类别名（与 mmaction2 默认一致）

### §9.2 ann_file 格式（mmaction2 RawframeDataset / VideoDataset）

```
videos_train/xxx.mp4 <label>
```

每行一个视频相对路径 + 一个 label 整数。整数与 classes.txt 行号对应（0-indexed）。

### §9.3 与各数据集的对应

| 数据集 | ann_file 路径 | 备注 |
|---|---|---|
| quadruped_action | `datasets/quadruped_action/quadruped_action_{train,val,test}_list.txt` | 占位骨架 |
| cats v1 | 需要生成（annotation_*.zip 解析后） | 工具待补 |
| mammal_v0 | `datasets/mammal_v0/ann_*.txt` | 待补 |
| UCF101 | NAS 官方 splits | 详 NAS 文档 |

---

**相关文档**：[3 号《模型》](../wiki/models)（用什么模型训这些数据）/ [4 号《训练体系》](../wiki/training-guide)（mmaction2 怎么加载这些数据）/ [6 号《系统架构》§4](../wiki/architecture)（数据如何进入管线）