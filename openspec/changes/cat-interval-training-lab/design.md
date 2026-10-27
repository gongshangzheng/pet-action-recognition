# 设计

- 数据源：`datasets/cat_raw/annotations/intervals.csv` 与 `datasets/cat_raw/videos/`。原区间按 1 起始、两端包含解释；训练前逐视频验证区间不超出 Decord 帧数。
- 仅用于首轮基线的六类：活动、进食、静止、饮水、理毛、抓挠。暂排除少样本类别；也排除不足 60 帧及与任何其他动作区间重叠的候选。空隙不作负样本。每类选 40/12/12 条用于 train/val/test；从固定的候选种子顺序中选择首个各类数量充足的拍摄日划分，并记录该种子，拍摄日期绝不跨集合。
- 当前仅做 smoke test：六类各取训练 2 条、验证 1 条、测试 1 条，拍摄日隔离，独立写入 `datasets/cat_interval_smoke/`；正式数据划分等待确认。自定义 `IntervalVideoDataset` 读取 JSONL 索引；`RestrictFrameRange` 在 DecordInit 后将 `total_frames` 和 `start_index` 限定到原区间，再使用 MMACTION2 标准 `SampleFrames`。不复制或重编码原视频。
- smoke test 使用 TSN ResNet50，三段稀疏采样、224 像素输入，预训练只加载 backbone，分类头六类随机初始化。仅运行一个 epoch，验证训练、验证、测试和产物记录全链路；不据此判断模型表现。
- 自定义指标在 val/test 输出 top1、macro-F1、各类 precision/recall/F1、混淆矩阵及逐样本概率。smoke 数据索引、配置、checkpoint、环境版本与终端日志一并归档到 `results/training/cat_interval_smoke/`。
- 重叠多猫、稀少行为、未标注空隙和逐猫身份均不由该单标签基线解决；它们保留在原标注中，结果不用于推断连续视频事件漏检率。

## 2026-10-27 规格完整性复核

五项实施任务已有完成记录；smoke 只证明链路可运行，不提供准确率结论。目前缺少 delta spec，尚不具备归档条件。本轮 update 仅修改既有工件；后续需创建规格，覆盖区间内采样、按日期隔离的小样本划分、独立产物路径及禁止效果外推，再做严格校验。
