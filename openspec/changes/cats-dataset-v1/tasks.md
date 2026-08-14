j# CATSUUuuuuuuuu-DATASETuuuuuuuuuuuuu::q
-v1 Tasks

## Phase 1：数据集构建

- [x] **T1.1** 在 pet 上执行 `scripts/slice_cats_clips.py`
- [x] **T1.2** 创建软链接
- [x] **T1.3** 验证数据集

## Phase 2：代码注册

- [x] **T2.1** 更新 `server/config.py`
- [x] **T2.2** 更新 `server/routers/training.py`
- [x] **T2.3** 本地验证

## Phase 3：模型训练

> ⚠️ VideoMAE 族从模型注册表中移除（见 T3.0）。最终训练模型为 TSM / SlowOnly / TimeSformer（共 3 个）。

- [x] **T3.0** 移除不可训练的 VideoMAE 模型

- [x] **T3.1** 训练 tsm-resnet50 ✅
  - Val top1: 62.5%，best epoch 10，inference 1057MB

- [x] **T3.2** 训练 slowonly-resnet50 ✅
  - Val top1: 67.05%，best epoch 10

- [x] **T3.3** 训练 timesformer-divst ✅
  - Val top1: 59.09%，best epoch 1，inference 734.6MB

每个训练通过 web 页面或 API 触发，监控训练日志，确保 metrics.json 正确写入。

## Phase 4：结果分析

- [x] **T4.1** 收集 3 个模型的训练指标
  | 模型 | Cats val top1 (best ckpt) | Best epoch | Final ep15 | Top5 |
  |------|-------------------------|-----------|------------|------|
  | TSM | **75.00%** | 10 | 62.50% | 100% |
  | SlowOnly | **67.05%** | 10 | 59.09% | 100% |
  | TimeSformer | **64.77%** | 1 | 59.09% | 100% |

- [x] **T4.2** 与 pet_action_mammal_v0 结果对比
  | 模型 | Mammal val (7类) | Cats val (5类) | Cats/Mammal diff |
  |------|----------------|----------------|----------------|
  | TSM | 73.61% @ ep9 | 75.00% @ ep10 | +1.39pp |
  | SlowOnly | 71.76% @ ep10 | 67.05% @ ep10 | -4.71pp |
  | TimeSformer | 75.00% @ ep3 | 64.77% @ ep1 | -10.23pp |

  **观察**：TSM 在 cats 上表现更好；SlowOnly 略降；TimeSformer 下降最显著（过拟合快，best 在 ep1）。
