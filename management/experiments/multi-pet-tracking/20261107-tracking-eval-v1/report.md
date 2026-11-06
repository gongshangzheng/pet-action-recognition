---
title: "多宠物 SORT 跟踪：OC-SORT 接入与 10 段评估（对照原版 SORT）"
date: "2026-11-07"
run_id: "tracking-eval-20261107a"
status: "partial"
verdict: "inconclusive"
summary: "OC-SORT 接入后在 10 段稳定多宠物区间上完成三指标评估：碎片/个体最大 4 超出阈值 ≤2，锚点一致性中位 0.82；与关闭全部 OC 机制的 SORT 基线逐帧等价（0 差异），碎片化主因是漏检间隙而非关联错误。人工核对 3 段叠加视频进行中，最终结论待 2.4/2.5。"
source: "results/tracking_eval_20261107/metrics_ocsort_v1.json"
---

## 背景与目标

（缺失：背景与目标未提供，待补充。）

## 当前问题

stride=5（3Hz）检测锚点 + 框不完美条件下，SORT 系跟踪能否为多宠物区间建立稳定轨迹？OC-SORT 的方向代价（OCM）与低分二次关联（use_byte）相对原版 SORT 是否有增益？

## 实验设计

（缺失：实验设计未提供，待补充。）

## 结果与分析

（缺失：结果与分析未提供，待补充。）

## 结论与下一步

碎片/个体最大 4 > 阈值 2，按事先阈值判不达标；但 SORT 对照显示轨迹与基线逐帧相同，根因方向指向观测密度/漏检而非算法选型——design 4.3 的 stride=2 复测是下一步。人工核对未完成前不给最终接入结论。

## 附录：配置与完整数据

### 环境与配置

- 模型: 跟踪：boxmot 25.0.0 OcSort（use_byte=True, inertia=0.2, max_age=8, min_hits=2, iou_threshold=0.2）；检测：GroundingDINO（既有缓存，box_threshold=0.3, stride=5）
- 数据集: cat_raw 检测缓存 2,573 段（full_run + 11-07 补检测批次）；区间表 intervals.csv sha256 80da23af
- 配置: 物种分实例（cat 流原 id / dog 流 +10000）；碎片聚类 gap≤24 锚点；交换信号 IoU>0.5
- 运行时间戳: 2026-11-07T02:40-03:45Z
- 执行入口: scripts/track_multi_pet.py + scripts/eval_multi_pet_tracking.py + scripts/select_multi_pet_eval.py
- 随机种子: 20261107

### 局限与边界

无逐帧身份 GT：交换次数只能用代理信号（同物种轨迹对 IoU>0.5 共享帧计数，本轮全 0）+ 人工核对裁决；碎片聚类用时间近邻启发（gap≤24 锚点）；use_byte 在置信度下限 0.30=box_threshold 的缓存上结构性不触发；评估集仅 10 段。

### 来源与核查

- run 产物：results/tracking_eval_20261107/metrics_ocsort_v1.json
- 详细来源见 manifest 各条目的 source 字段；单位、样本量与局限见 manifest 的 metrics 条目。
- 指标与趋势见 metrics.json（series 折线 + tables 指标表）。

