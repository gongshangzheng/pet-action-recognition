# 猫动作训练第一版：七类标签与模型选择

日期：2026-10-24，状态：Plan（待 Review）。

## Why

现有 `cat-interval-training-lab` 已用 6 类极小样本验证 MMAction2 区间读取、训练、测试和产物记录链路，但正式训练仍面对原始 12 类标签：异常类样本极少，按原类别无法形成可训练、可评估的闭集。用户确认第一版沿用“丢弃重叠区间”的单标签协议，将异常行为合并为一个独立类，并把如厕单独设为一类；多猫追逐/打闹不进入 v1，后续计划用空间关系逻辑识别，不依赖动作分类模型。本 change 负责把该协议落成可复现、可回滚的派生标签，并在同一数据协议下选择第一版训练模型。

## What Changes

- 生成 v1 派生标签，不修改原始视频和原始标注：
  - 常见类：`activity`、`eating`、`drinking`、`prolonged_stationary`、`grooming`、`toileting`
  - 异常类：`abnormal`，合并 `abnormal/scratching`、`abnormal/gnawing`、`abnormal/fall`、`abnormal/seizure`
- 沿用现有过滤：原始区间按 1-based、两端包含解释；区间少于 60 帧丢弃；与同视频内任意其他区间重叠则丢弃。
- 按拍摄日隔离 train/val/test；训练集使用全部过滤后的候选，不再限制每类 40 条；验证/测试保留自然分布，并另生成平衡诊断集。
- 生成映射表、数据审计、划分清单和 SHA-256；原始标注只读；改动前备份本地与远程工作树；代码、配置和报告入库。
- 在同一数据协议下对比 TSN R50 与 TSM R50，按验证集 macro-F1 为主、分类别召回（尤其 `toileting`、`abnormal`、`grooming`、`drinking`）为辅选择第一版模型；测试集只做最终报告，不参与模型选择。

## 已确认的数据事实

- 原始 `datasets/cat_raw/annotations/intervals.csv`：3,927 条区间、2,573 个视频、114 个拍摄日、12 个标签。
- 按 v1 映射和过滤后：2,735 条候选；丢弃 640 条不足 60 帧、518 条重叠、34 条 v1 未纳入标签（多猫追逐/打闹）。
- 视频帧校验再用 Decord 排除 25 条帧越界区间，最终 **2,710 条候选**：`activity` 1,629、`eating` 341、`prolonged_stationary` 335、`drinking` 164、`grooming` 85、`abnormal` 125、`toileting` 31。
- 使用与现有脚本相同的拍摄日划分搜索规则，实际 seed 1 可行（70 训练日 / 22 验证日 / 22 测试日）；自然分布候选 **train 1,664、val 604、test 442**。其中 `toileting` 为 20/4/7（train/val/test），验证侧只有 4 条，样本很紧。最终数字以服务器审计为准。

## 类别映射

| 原始标签 | v1 类别 |
|---|---|
| `common/activity` | `activity` |
| `common/eating` | `eating` |
| `common/drinking` | `drinking` |
| `common/prolonged_stationary` | `prolonged_stationary` |
| `common/grooming` | `grooming` |
| `common/toileting` | `toileting` |
| `abnormal/scratching`、`abnormal/gnawing`、`abnormal/fall`、`abnormal/seizure` | `abnormal` |

v1 不纳入：`common/multi_cat_chase`、`common/multi_cat_roughplay`（共 34 条源区间）。多猫追逐/打闹后续计划用空间关系逻辑（相对距离、速度、位置变化、停留区域等）识别，不依赖动作分类模型；本批数据没有呕吐/猫叫样本。`fall`、`seizure` 过滤后为 0，`gnawing` 仅 4 条，因此 `abnormal` 实际以 scratching 为主，不拆独立异常类。

## Non-goals

- 不训练多猫追逐/打闹分类器；后续用空间关系逻辑或跟踪规则处理。
- 不加入呕吐/猫叫、独立抽搐/跌落/啃咬类；这些留到后续数据补充或单独 change。
- 不做多标签、多猫身份关联、按猫裁剪或时间轴事件级评测。
- 不修改原始视频、原始标注、既有 smoke 产物或既有模型 checkpoint。
- 不在本轮规划中生成标签、启动训练或修改服务器文件；Apply 阶段才执行。

## Capabilities

### New Capabilities

- `cat-action-training`

## 验收

- 派生标签、映射、审计、划分和 SHA-256 生成并可复核；原始标注字节和 SHA-256 不变。
- 训练使用全部过滤后的训练候选，验证/测试自然分布和平衡诊断集均可重建；`toileting` 的低样本数在报告中明确标注。
- 验证/测试报告单列合并后的 `abnormal` 整体 recall 和 support，不声称四个异常子类各自可识别。
- TSN R50 与 TSM R50 在同一划分、同一采样和同一评估口径下完成训练与验证，并记录选择依据。
- 本地和远程改动前备份存在且可恢复；报告记录备份路径、数据/配置/checkpoint 哈希和运行环境。
- 没有把密码、`4090.txt`、数据、checkpoint 或 `results/` 提交进 Git；远程未发生直接手工改文件。
