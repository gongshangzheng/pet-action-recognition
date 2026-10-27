# 设计

## 配置

`configs/cat_action_v1_base.py` 放共享的数据索引、dataloader、`CatIntervalMetric` 和 loop 设置；每个模型一个子配置，通过 `_base_` 继承它和 `default_runtime.py`（SlowFast/X3D 另继承 vendored 模型 base）。类别权重沿用 v1 的 `[0.488, 1.090, 1.599, 1.049, 2.225, 3.448, 1.634]`。

| 模型 | batch × 累积 | 优化器 | lr | 说明 |
|---|---|---|---|---|
| VideoMAEv2-B | 4 × 4 | AdamW wd 0.05 | 5e-5 | AMP，drop_path 0.1 |
| UniFormerV2-B | 16 × 1 | AdamW wd 0.05 | 5e-5 | AMP |
| X3D-S | 16 × 1 | SGD m0.9 wd 1e-4 | 0.01 | AMP |
| SlowFast R50 | 8 × 2 | SGD m0.9 wd 1e-4 | 0.005 | AMP |

调度：2 epoch 线性 warmup + cosine，共 20 epoch，每 epoch 验证，按 `macro_f1` 存最佳。

X3D 不用 `target_fps`：源视频 15 fps，间隔 3 帧的时间跨度等于 K400 30 fps 下间隔 6 帧。

## 执行

- 复用 `scripts/run_cat_action_v1.py` 的 `train_model`/`test_model`；新增 `scripts/run_cat_action_batch.py` 提供三个阶段：`train`（按设备队列顺序训练，失败不中断队列）、`rank`（只用验证集给 6 个模型排名并冻结）、`test`（排名之后才跑 test）。
- 静态分配：GPU 0 先 VideoMAEv2 再 X3D；GPU 1 先 UniFormerV2 再 SlowFast。开跑前查 `nvidia-smi`，不抢占他人任务。
- 预检脚本 `scripts/check_cat_action_models.py`：构建模型、加载权重并比对 backbone 张量、核对首样本帧落在区间内、用真实 batch 跑一次前向/反向测显存。
- 服务器侧沿用 bundle 同步到 `~/pet-final-v1`，不手改远程文件。

## 风险

- 解码是瓶颈：SlowFast 每样本读 32 帧，估计单模型约 5 小时，排在队尾，可随时取消。
- 验证集 `abnormal` 18 条、`toileting` 4 条，macro-F1 差 3 个点以内不能当作真实差距。
- 与基线不是严格受控对比（见 proposal 的差异清单）。
