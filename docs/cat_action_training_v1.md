# 猫动作训练 v1：已并入实验报告

本页原本记录七类区间基线的训练协议、结果与风险（2026-10-25 定稿）。内容已在 2026-11-12 合并进实验报告：

- 报告：`management/experiments/cat-action-v1/20261025-seven-class-baseline/report.md`（页面上是 `/management/experiments?topic=cat-action-v1`）
- 合并范围：七类区间基线的 TSM/TSN 对比、六模型参考批次、链路验证（原 `docs/lab_cat_training_smoke.md`）、早期 79 段五类实验的历史对照。
- 原文完整正文仍可从 Git 历史取回：`git show b1d9fe31:docs/cat_action_training_v1.md`。

## 保留的产物与哈希清单

这些指针在报告附录里已有对应条目，此处保留是为了让归档 change 里的路径引用仍能落到具体文件。

- 数据索引（seed 1，`datasets/cat_action_v1/`，不入库）：train `073350c27fbda36c4a931fb0852f20a495023cfe7298e2350c677dfa9962751c`、val `21b7bb44d8450d210bb9a73d9f951ec8e3a571ab97a79e379d5b487c6e2eb1d6`、test `058c08bcd78554d70714533140d712c8e1db50c5398d199d711be61653d4096e`
- 原始标注 SHA-256：`80da23af3c6a6db4bac739fc2c1dc8714b8b5dc063b55abe7c9762932eeb04ff`
- TSM R50 best checkpoint（epoch 16）：`results/training/cat_action_v1/tsm_r50/work/best_macro_f1_epoch_16.pth`，SHA-256 `1cf934fcb318dbe7cd50f2e7bcdfd2e22f425354109383dedafb9a6a9e845193`
- TSN R50 best checkpoint（epoch 20）：`results/training/cat_action_v1/tsn_r50/work/best_macro_f1_epoch_20.pth`，SHA-256 `d75ebf54a807d804796d8a9d23362c8e958db593b36df6d2c49b359672c39b2c`
- 参考批次 best checkpoint（前缀）：VideoMAEv2-B `39a1baa176d66b85`、X3D-S `00e09d3b61648fe1`、SlowFast-R50 `09d095beb8da739b`、UniFormerV2-B `b1ddd98c99328284`
- 配置 SHA-256：TSM R50 `0c36a873ce8d491dfd83a5e7ba79824cd9477ac5c7f3a803926f281255118d52`、TSN R50 `22c0937c67cfeff16cac641f9f01c852824cf298bd7b6d66763cedfb2362f25b`
- 排名与汇总：`results/training/cat_action_v1/model_zoo_ranking.json`（冻结于 2026-10-25T03:16:42Z）、`model_zoo_summary.json`、`selection.json`
