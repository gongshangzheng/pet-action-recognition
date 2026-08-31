# fix-training-api-device-pretrained Proposal

## Why

训练/测试链路有两个 argparse 级 bug，导致通过 API（或前端）发起的训练**静默失败**：子进程秒退、run 永远卡在 "started"、无任何报错（stderr 被 DEVNULL 吞掉）。2026-08-24 批量跑 cats 数据集时实测触发——15 个模型的训练任务全部启动即死。

两个 bug：

1. **`--device` 不支持选卡**：`train_model.py` / `run_test.py` 的 `--device` choices 只有 `cuda/cpu`，而 API（`server/routers/training.py`）把 `cuda:0`/`cuda:1` 原样透传 → argparse 拒绝。pet 是双卡共享机，选卡是刚需（testing skill 文档也写了 `--device cuda:0/1` 用法）。
2. **`--pretrained` 语义断裂**：CLI 定义为 `store_true` 开关，API 却传 `--pretrained=<url>`（带值）→ argparse 报 `ignored explicit argument`。即使传对了 `-p`，现有逻辑也会生成 `load_from=True` 这种无效 cfg-option——pretrained finetune 模式经 API 完全不可用。

## What Changes

- **`scripts/train_model.py`**：
  - `--device` 放开 choices，接受 `cuda` / `cuda:N` / `cpu`；`cuda:N` 通过子进程环境变量 `CUDA_VISIBLE_DEVICES=N` 实现选卡（mmaction2 train.py 本身无 --device 参数），进程内仍按 `cuda:0` 逻辑运行
  - `--pretrained` 从 `store_true` 改为**带值参数**（URL 或本地 ckpt 路径），语义 = `-l/--load-from`（加载整模权重做 finetune，cfg-option `load_from=<url>`）；裸 `-p`（不带值）变为非法并给出提示
- **`scripts/run_test.py`**：`--device` 同样放开接受 `cuda:N`（同样的 `CUDA_VISIBLE_DEVICES` 方案）
- **`server/routers/training.py`**：不改传参格式（现状即为目标格式），仅确认透传契约成立
- **验证**：argparse 级用例（`cuda:1` / `--pretrained=<url>` / 裸 `-p` 报错）+ pet 上真实发起一次 API 训练确认不再秒挂

**BREAKING（CLI 层）**：`train_model.py` 裸 `-p` / `--pretrained`（不带值）从"合法但语义错误"变为报错；带值用法此前直接报错，无存量兼容负担。

不改动（Non-goals）：

- 不解决"子进程秒退时 run 状态卡 started"的可靠性问题（需 API 捕获子进程早期退出码，另开 change）
- 不动 `inference.py` / `speedrun.py`（已支持 `cuda:N`）
- 不动四模式互斥语义与 registry 结构

## Capabilities

### New Capabilities

- `training-launch-contract`：训练/测试启动接口契约——CLI 参数（`--device` 选卡、`--pretrained` 带值）与 API payload（`device`、`pretrained`）的合法取值、映射语义与非法输入的报错行为

### Modified Capabilities

（无——现有 `speedrun-results`、`tools/md-to-docx` spec 不受影响）

## Impact

- **代码**：`scripts/train_model.py`（argparse + env 注入）、`scripts/run_test.py`（argparse + env 注入）
- **API**：`POST /api/training/run`、`POST /api/training/run_test` 的 `device`/`pretrained` 字段从"传了会静默失败"变为真正可用；前端训练页选卡/预训练模式解锁
- **同步**：pet 工作区与本地这 3 个文件当前 md5 一致，修复后可直接 rsync 同步（push 被 pet 脏工作区阻塞，属既有问题，不在本 change 解决）
- **风险**：极低——改动集中在 argparse 定义与一处 env 注入；存量"能跑"的调用方式（`--device cuda`、不传 pretrained）行为不变
