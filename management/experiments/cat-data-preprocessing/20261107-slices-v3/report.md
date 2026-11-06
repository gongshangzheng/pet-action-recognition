---
title: "猫行为片段数据集构建：从 3,927 个标注区间到 6,363 个片段"
date: "2026-11-07"
run_id: "slices-v3"
status: "partial"
verdict: "inconclusive"
summary: "补齐 429 段未检测视频后，按“类别闭集十类 + 去短于 1 秒 + 多宠物排除 + 重叠仲裁 + 短区间外延 + 分层随机切片 + activity 上限”产出 6,363 个片段；多宠物判定的静物误检尚未校准，结论不完整。"
source: "results/cat_data_preprocessing/slices_v3"
---

## 背景与目标

（缺失：背景与目标未提供，待补充。）

## 当前问题

在只有 GroundingDINO 检测、没有个体跟踪的条件下，能否把 3,927 个标注区间整理成长度均衡、可追溯的片段集合，并把每一层损失归因到具体规则？

## 实验设计

（缺失：实验设计未提供，待补充。）

## 结果与分析

（缺失：结果与分析未提供，待补充。）

## 结论与下一步

管线可跑通并给出可核对的分层损失（3,927 → 2,867 区间 → 6,363 片段）。但在静物误检校准前，多宠物排除量（968）不可信，因此本报告判为 partial / inconclusive；下一步先做 20 条人工判定，再实现静物过滤并重跑。

## 附录：配置与完整数据

### 环境与配置

- 模型: GroundingDINO-tiny（采样检测，stride=5）
- 数据集: cat_raw 2,737 段事件视频 / 3,927 个标注区间
- 配置: clip 60 帧、每区间最多 4 片段、分层随机起点 seed=0、多宠物阈值覆盖≥0.5 且连续≥3 锚点、activity 上限 3×第二大类
- 运行时间戳: 2026-11-07 03:33（slices_v3）；补检测 2026-11-07 02:55 完成
- 执行入口: scripts/build_cat_dataset_slices.py；scripts/remote/run_missing_detection.sh
- 随机种子: 0

### 局限与边界

多宠物判定依赖检测计数，毛绒玩具/摆件/海报会被判成第二只宠物（seizure 区间即因此被排除）；20 条抽查尚待人工判定；片段清单缺猫数、狗数字段；activity 占用仍达 55%。

### 来源与核查

- run 产物：results/cat_data_preprocessing/slices_v3
- 详细来源见 manifest 各条目的 source 字段；单位、样本量与局限见 manifest 的 metrics 条目。
- 指标与趋势见 metrics.json（series 折线 + tables 指标表）。

