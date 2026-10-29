# Proposal: 共享 GPU/CPU 资源护栏（resource-guard）

## Why

pet 是**多人共享机**（现有 16 个用户在线，别人在跑训练）。2026-10-27/28 期间跑门控全量标注（`label_gate_native.py --tiles 3`）时：

- 主机 **load average 冲到 103**（4K HEVC 逐帧解码 + 每帧 9 次 GroundingDINO 前向）；
- 期间 **frp 隧道连挂两次**：SSH 从「banner 超时」→「Connection refused」，最长一次连续 10 分钟不可达；
- 我新写的三个脚本（`label_gate_native.py`、`recheck_gate_dog_labels.py`、`train_gate.py`）**没有任何资源护栏**：
  不查他人进程、不限 torch/cv2 线程数、不设显存上限、运行中不复查、被抢占也不让行。

现有 skill 只有**人工纪律**（`remote-server-discipline` §5：「开跑前 nvidia-smi 查占用」「禁止抢占」），
没有任何**代码级**执行机制；也没有「实验管理」类 skill（`testing` 讲怎么跑测试、`speedrun` 讲批量标注用法，
都不涉及资源预算与让行协议）。**这条缺口由我自己踩到了，需要补机制而不是只补文档。**

## What Changes

- 新增共享护栏模块 `scripts/_resource_guard.py`，四层：
  1. **预检拒绝**：目标卡空闲显存/利用率不达标、存在他人计算进程、主机 load 或可用内存超阈 → 直接拒绝开跑（可 `--force` 但需显式标注）；
  2. **运行时限额**：`torch.set_num_threads` / `OMP_NUM_THREADS` / `cv2.setNumThreads` / DataLoader `num_workers` 上限、`torch.cuda.set_per_process_memory_fraction` 显存上限、`nice`/`ionice` 降权；
  3. **合作式让行（yield）**：每 N 秒复查一次，发现他人计算进程出现 / 显存被占 / load 超阈 → 暂停（`SIGSTOP` 自身子进程或保存进度退出），条件恢复后再续；
  4. **资源轨迹**：JSONL 记录（时间、显存、util、load、线程数），结束时给峰值/均值汇总，落 `results/<task>/resource_trace.jsonl`。
- 接入现有脚本：`label_gate_native.py`、`recheck_gate_dog_labels.py`、`train_gate.py`（门控链路），并给 `gpu_watcher.py` 增加「运行中监控」模式（目前只在点火前判定）。
- 新增 skill `.claude/skills/experiments/SKILL.md`：实验前 checklist（资源预检/预算/预计耗时）、运行中让行协议、产物与登记（run registry）、事故记录表。
- 把本次事故写进 `remote-server-discipline` 的翻车案例表。

## Capabilities

### New Capabilities

- `resource-guard`: 共享 GPU/CPU 上的任务前预检、运行时上限、合作式让行与资源轨迹的强制契约。

## Impact

- 影响：`scripts/_resource_guard.py`（新增）、门控三脚本、`scripts/checks/gpu_watcher.py`、两个 skill 文档。
- 不改任何算法/数据产物；只增加「开跑前拒绝」「运行中限额」「让行」三类行为。
- 验收含一次**演练**：伪造他人占卡 → 预检必须拒绝；运行中插入占用进程 → ≤60 s 内暂停/退出并留痕。
