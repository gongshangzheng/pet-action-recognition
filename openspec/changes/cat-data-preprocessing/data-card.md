# 猫行为闭集数据集 数据卡（草案）

本卡随预处理推进逐步补齐；数字均标注来源，未完成的字段写明缺什么。

## 1. 类别表（2026-11-07 用户确认）

| 序号 | 类别 | 原始标注 | 状态 |
|---|---|---|---|
| 1 | activity | common/activity | 进闭集 |
| 2 | prolonged_stationary | common/prolonged_stationary | 进闭集 |
| 3 | eating | common/eating | 进闭集（后续可能移交空间关系层） |
| 4 | drinking | common/drinking | 进闭集（同上） |
| 5 | toileting | common/toileting | 进闭集（同上） |
| 6 | grooming | common/grooming | 进闭集 |
| 7 | scratching | abnormal/scratching | 进闭集 |
| 8 | gnawing | abnormal/gnawing | 进闭集 |
| 9 | fall | abnormal/fall | 进闭集（后续移交空间关系层） |
| 10 | seizure | abnormal/seizure | 进闭集，仅 1 条区间，报告单列 support |

不进入闭集：`common/multi_cat_chase`、`common/multi_cat_roughplay`（交多目标关联层，见 change `multi-pet-sort-tracking`）。

## 2. 语料规模

| 项 | 数值 | 来源 |
|---|---:|---|
| 事件视频 | 2,737 段 | `ls cat_raw/videos` |
| 人工标注区间 | 3,927 条（12 类） | `cat_raw/annotations/intervals.csv` |
| 可映射区间（排除 multi_cat_*） | 3,893 条 | 按 label_mapping 过滤 |
| 带映射标注的视频 | 2,573 段 | intervals.csv 去重 |
| 已检测视频 | 2,144 段 | `assets/full_run/metadata` |
| 未检测视频 | 429 段 / 807 区间 | 差集，补检测进行中 |
| 旧七类索引 | 2,710 条 | `cat_action_v1/{train,val,test}.jsonl` |
| 旧裁剪可用区间 | 207 条（猫） | `gdino-v1-cat/manifest.json` |

## 3. 已知问题

- **eating / drinking 跨视频混淆**：同一只猫脸图案碗在不同视频里分别被标成 eating 与 drinking；远景下无法从画面上区分粮与水。本轮不处理，只在此标注。
- **多宠物（猫+狗）普遍**：已检测视频中 1,616 段（75%）出现过狗；区间级 1,541 条为“1 猫 + 1 狗”。按稳定性判据（覆盖 ≥0.5 且连续 ≥3 锚点），565 个区间为稳定多宠物。
- **标注无身份字段**：多宠物区间里无法确定标注指哪只动物。
- **长区间多为事件级标注**：非 activity、非 prolonged_stationary 的区间中，81 个超过 60 秒、7 个超过 120 秒，起点常为 0.1 秒、终点接近视频末尾。
- **单帧与极短区间**：33 条短于 1 秒（含 4 条单帧），判断为行为起点或事件级标记，已决定排除。

## 4. 处理规则摘要

- 短于 1 秒（<15 帧）排除，记 `too_short_annotation`。
- 1–4 秒左右外延到 60 帧，用真实相邻帧，不越视频边界、不跨其他区间。
- 片段 60 帧，分层随机起点（区间切 k 段，k = min(4, 可容纳数)），每区间最多 4 个片段，预处理阶段一次性产出。
- activity 训练/测试取子集（按视频抽样，约与第二大类持平），种子固定。
- 评测 `num_clips=1`，不引入官方 5 窗口平均。

## 5. 待补字段

- 新索引的区间数、片段数、各类片段分布（等 8.1）。
- 多宠物与无检测的最终排除量（等 3.2）。
- 重叠仲裁后的类别分布（等 4.3）。
