## 1. 训练

- [x] 【移交】1.1 预检 GPU 与主机资源，启动 20 epoch 训练（`configs/cat_clip_videomaev2_b.py`）。判据：运行日志路径、守卫日志、退出码写入 evidence；首轮 loss 低于 ln(10)。（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】1.2 训练完成后核对产物：`best_macro_f1_epoch_*.pth` 存在，状态文件为完成，检查点含优化器与调度器状态。判据：文件清单与字段核对写入 evidence。（后续在 cat-pipeline-consolidation 执行）

## 2. 冻结测试

- [x] 【移交】2.1 用最佳检查点在 test（1,171 片段）上测试一次，保存逐样本预测与指标。判据：`test_metrics.json` 落盘，运行次数为 1。（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】2.2 按中期目标口径出数：可用率 3,339/3,927、条件准确率、端到端准确率、逐类 recall 与 support、按物种分组。判据：五项数字写入 evidence，并标出哪些类样本不足（seizure 0、fall 1、gnawing 13）。（后续在 cat-pipeline-consolidation 执行）
- [x] 【移交】2.3 写实验报告并更新 AGENTS.md 的当前基线。判据：报告生成器完整度 0 项缺失，基线数字与报告一致。（后续在 cat-pipeline-consolidation 执行）
