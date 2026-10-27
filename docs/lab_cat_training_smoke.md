# 课题组服务器猫动作训练流程验证

2026-10-23 在 `/home/wyy/pet-final` 用 TSN ResNet50 完成一次独立的 smoke test。目的仅是确认区间读取、视频解码、训练、验证、checkpoint、独立测试及结果记录全链路可运行；正式类别、划分和训练方案仍待确定。

- 数据：6 类，每类训练 2 条、验证 1 条、测试 1 条，共 24 条区间；按视频拍摄日隔离。原始视频与标注未改动。索引在 `datasets/cat_interval_smoke/`，筛选和视频帧数审计在 `results/training/cat_interval_smoke/data_audit.json`。
- 训练：GPU 1，batch size 2，1 epoch，6 个训练批次；训练完成并保存最佳 checkpoint，随后独立测试成功。记录含配置及数据索引 SHA-256、Torch/MMAction2 等版本、日志和 checkpoint 路径。
- 验证集：6 条，top-1 16.67%，macro-F1 5.56%，balanced accuracy 16.67%。测试集：6 条，top-1 33.33%，macro-F1 23.33%，balanced accuracy 33.33%。**每类测试只有 1 条，这些数值没有模型效果解释意义。**
- 完整性校验：`results/training/cat_interval_smoke/verification.json` 为 `verified`；确认 checkpoint 非空、三组索引哈希与运行记录一致、拍摄日不交叉、逐样本预测的 ID 完整、概率有限、混淆矩阵计数正确。

所有训练产物均在服务器 `/home/wyy/pet-final/results/training/cat_interval_smoke/`。其中 `run_status.json` 是运行概览，`train.log` 和 `test.log` 为终端记录，`val_metrics.json` 和 `test_metrics.json` 含分类别 precision/recall/F1、混淆矩阵与逐样本概率，`work/best_macro_f1_epoch_1.pth` 是本次流程验证权重。`preflight.json` 记录区间采样和解码检查。正式训练前需另行确定类别、样本筛选、划分和评估策略；不能把本次 checkpoint 或分数用于验收。
