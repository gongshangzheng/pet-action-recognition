# 课题组服务器猫动作训练流程验证：已并入实验报告

本页原本记录 2026-10-23 在 `/home/wyy/pet-final` 用 TSN ResNet50 做的一次 smoke test（6 类、24 条区间、1 epoch），目的只是确认区间读取、视频解码、训练、验证、checkpoint、独立测试与结果记录全链路可运行。

内容已合并进 `management/experiments/cat-action-v1/20261025-seven-class-baseline/report.md` 的「链路验证」一节，报告里同时写明：验证集 6 条 top-1 16.67%、测试集 6 条 33.33%，每类只有 1 条样本，这些数值没有模型效果解释意义；真正的产出是 `verification.json` 为 `verified`。

原文完整正文可从 Git 历史取回：`git show b1d9fe31:docs/lab_cat_training_smoke.md`。

产物仍在服务器 `~/pet-final/results/training/cat_interval_smoke/`（`run_status.json`、`train.log`、`test.log`、`val_metrics.json`、`test_metrics.json`、`preflight.json`、`verification.json`、`work/best_macro_f1_epoch_1.pth`）。
