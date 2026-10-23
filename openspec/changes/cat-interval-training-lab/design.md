# 设计

- 数据源：`datasets/cat_raw/annotations/intervals.csv` 与 `datasets/cat_raw/videos/`。原区间按 1 起始、两端包含解释；训练前逐视频验证区间不超出 Decord 帧数。
- 仅用于首轮基线的六类：活动、进食、静止、饮水、理毛、抓挠。暂排除少样本类别；也排除不足 60 帧及与任何其他动作区间重叠的候选。空隙不作负样本。每类选 40/12/12 条用于 train/val/test，固定种子，拍摄日期绝不跨集合。
- 自定义 `IntervalVideoDataset` 读取 JSONL 索引；`RestrictFrameRange` 在 DecordInit 后将 `total_frames` 和 `start_index` 限定到原区间，再使用 MMACTION2 标准 `SampleFrames`。不复制或重编码原视频。
- 基线使用 TSN ResNet50，三段稀疏采样、224 像素输入，预训练只加载 backbone，分类头六类随机初始化。先运行三个 epoch，验证流程与初步效果，随后再决定完整训练。
- 自定义指标在 val/test 输出 top1、macro-F1、各类 precision/recall/F1、混淆矩阵及逐样本概率。数据索引、配置、checkpoint、环境版本与终端日志一并归档到 `results/training/cat_interval_baseline/`。
- 重叠多猫、稀少行为、未标注空隙和逐猫身份均不由该单标签基线解决；它们保留在原标注中，结果不用于推断连续视频事件漏检率。
