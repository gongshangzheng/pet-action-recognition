# training-launch-contract Spec Delta

## Purpose

定义训练/测试启动接口（CLI 参数与 API payload）的合法取值与语义契约，保证 API 透传到 CLI 的每个参数都能被正确解析，杜绝"argparse 失败 → 进程秒退 → run 卡 started"的静默失败。

## ADDED Requirements

### Requirement: `--device` 支持 GPU 选卡

`train_model.py` 与 `run_test.py` 的 `--device` SHALL 接受 `cpu`、`cuda`、`cuda:N`（N 为非负整数）三种形式。`cuda:N` SHALL 通过对子进程注入 `CUDA_VISIBLE_DEVICES=N` 实现物理卡选择，进程内设备视图保持 `cuda:0`；`cuda` 等价于不设置该变量（沿用环境默认）。非法取值 SHALL 在启动前以非零退出码报错。

#### Scenario: 指定物理卡训练
- **WHEN** 以 `--device cuda:1` 调用 `train_model.py`
- **THEN** 训练子进程在 `CUDA_VISIBLE_DEVICES=1` 环境下启动，`nvidia-smi` 可见负载落在物理卡 1

#### Scenario: 默认行为不变
- **WHEN** 以 `--device cuda` 调用（或经 API 不传 device 字段）
- **THEN** 行为与修复前完全一致（不注入 `CUDA_VISIBLE_DEVICES`，用环境默认卡）

#### Scenario: 非法 device 报错
- **WHEN** 以 `--device gpu0` 等非法值调用
- **THEN** 进程在启动训练前以非零退出码退出，stderr 指明合法取值

### Requirement: `--pretrained` 带值语义

`train_model.py` 的 `--pretrained` SHALL 接受一个值（预训练权重的 URL 或本地路径），其语义 SHALL 等同于 `--load-from <值>`：整模权重作为初始化加载（cfg-option `load_from=<值>`），epoch 从 0 开始。裸 `--pretrained`（不带值）SHALL 报 argparse 错误。`--pretrained` 与 `--load-from`/`--resume`/`--from-scratch` 的互斥校验 SHALL 继续生效。

#### Scenario: API 带 URL 发起 pretrained finetune
- **WHEN** API 以 `pretrained: true`（registry 解析出 URL）或显式 URL 调用，透传 `--pretrained=<url>`
- **THEN** `train_model.py` 正常启动，训练命令含 `load_from=<url>`，进程不秒退

#### Scenario: 裸 -p 报错
- **WHEN** 以不带值的 `-p` / `--pretrained` 调用
- **THEN** argparse 以非零退出码报错并提示需要值

#### Scenario: 不传任何模式标志
- **WHEN** 既不传 `--pretrained` 也不传其他模式标志
- **THEN** 训练按 config 自带初始化（如 `init_cfg` 中的 ImageNet 权重）启动，与修复前一致

### Requirement: API 透传契约成立

`POST /api/training/run` 与 `POST /api/training/run_test` 接收的 `device`（`cuda`/`cuda:N`/`cpu`）与 `pretrained`（`true`→registry URL，或显式字符串）SHALL 能原样透传到 CLI 并被成功解析；合法 payload SHALL NOT 因子进程 argparse 失败而静默卡死。

#### Scenario: 前端发起 cuda:1 + pretrained 训练
- **WHEN** 经 API 提交 `{model_id, dataset_id, device: "cuda:1", pretrained: true}`
- **THEN** 训练进程真实启动，run 状态进入 `running` 且 loss 随时间更新（可在 `/api/training/runs` 观察到进度）
