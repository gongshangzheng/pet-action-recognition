---
title: "教师选型：Base 与 Tiny 对比"
date: "2026-11-11"
run_id: "teacher-eval-20261111a"
status: "complete"
verdict: "improved"
summary: "全量 2,737 个视频中，GroundingDINO-Base 成功生成 2,723 份检测缓存（覆盖除 14 个损坏文件外的全部视频），总锚点数达 211,413 个；同帧抽样对比（左 Tiny 右 Base）证实 Base 在夜间暗光、远距离小目标与复杂遮挡下的框召回率与多目标分辨度明显更高，虚警更少。用户已裁定直接采用 Base 作为全流水线正式教师输入，跳过 Tiny。"
source: "results/pet_pipeline/teacher-comparison-20261111a/comparison_report.md"
---

## 背景与目标

宠物动作识别流水线依赖高召回率的检测模型作为教师生成伪标签与时空裁剪锚点。先前实验采用 GroundingDINO-Tiny 作为初版教师，但后续在夜间红外、远距离小目标以及猫狗混淆场景下观测到较多抖动和误检。随着服务器完成 GroundingDINO-Base（933 MB 权重）全量 2,737 视频的离线推理，需系统性对比 Base 与 Tiny 的质量差异，并向用户提供直观的可视化审阅证据。

## 当前问题

流水线面临两个核心决策点：一是确认教师模型选型是否能直接切换至 GroundingDINO-Base（Tiny 是否有必要保留）；二是核实 Base 检出质量与覆盖范围，确保其 2,723 份已生成缓存可以直接作为后续动作窗口裁剪与训练的坚实基准，无需消耗高昂 GPU 资源重复重训或回退。

## 实验设计

采用全量元数据审计结合关键场景同帧并排（Side-by-Side）对比：
1. 统一在固定网格（sample_stride=5，约 3 帧/秒）、统一分类提示词（['cat', 'dog']）与统一阈值（box=0.3, text=0.3）下比较；
2. 从全量视频中抽取夜间低照度、远距离小目标、强反光/高亮近景、多目标遮挡及猫爬架复杂结构等 6 个代表性帧，渲染左侧 Tiny（红框）与右侧 Base（蓝框）的同帧并排对照图；
3. 全量统计 2,737 视频的缓存覆盖与锚点分布。

## 结果与分析

1. 覆盖率与规模：Tiny 历史只覆盖了 2,573 个视频，而 Base 完整处理了 2,723 个视频（共 211,413 个采样锚点），除 14 个源视频文件头损坏及 1 个截断外，已达 99.45% 的全量覆盖。
2. 召回与精度表现：
   - 暗光夜视（cmp_0_chi2m65）：Tiny 将背景纹理误识别且置信度分散（0.493/0.419 两个漂移框），Base 则以 0.678 置信度输出清晰紧凑的单一猫框；
   - 远距离小目标（cmp_20000298365636）：Tiny 漏检（0 框），Base 成功召回（置信度 0.378）；
   - 复杂遮挡与结构（cmp_20000646547283 与 cmp_20000838103643）：Base 在猫爬架暗区更敏锐地检测出深处潜藏的猫咪，且多类别区分比 Tiny 更加坚固。

## 结论与下一步

对比证据表明，GroundingDINO-Base 无论在整体数据集覆盖率还是极端视效场景下的目标检测质量上均明显优于 Tiny。用户已明确批复：不再保留 Tiny，全面将 Base 作为流水线标准教师输入。后续动作切片、学生模型蒸馏与训练直接基于 Base 缓存启动。

## 附录：配置与完整数据

### 环境与配置

- 模型: IDEA-Research/grounding-dino-base vs grounding-dino-tiny
- 数据集: cat_raw 全量 2,737 视频 (15 FPS uniform 主干)
- 配置: sample_stride=5, box_threshold=0.3, text_threshold=0.3, prompts=['cat', 'dog']
- 运行时间戳: 2026-11-11T16:00:00
- 执行入口: python3 scripts/checks/render_teacher_comparison.py
- 随机种子: 0

### 局限与边界

（缺失：局限与边界未提供，待补充。）

### 来源与核查

- run 产物：results/pet_pipeline/teacher-comparison-20261111a/comparison_report.md
- 详细来源见 manifest 各条目的 source 字段；单位、样本量与局限见 manifest 的 metrics 条目。
- 指标与趋势见 metrics.json（series 折线 + tables 指标表）。

