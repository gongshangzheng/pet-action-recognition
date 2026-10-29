# Tasks: resource-guard-shared-gpu

## 1. 模块与限额

- [ ] 1.1 `scripts/_resource_guard.py`：`preflight(cfg) -> Report`（GPU 空闲/他人进程/load/内存/磁盘五项）、`apply_limits(cfg)`（torch/OMP/cv2/DataLoader/显存 fraction/nice）、`yield_watch(cfg, on_pause)`、`trace(event)`。
- [ ] 1.2 拒绝路径：不满足条件时打印原因表并以退出码 3 结束；`--force` 必须配 `--force-reason` 并写入轨迹。
- [ ] 1.3 单元级验证：`torch.get_num_threads()`、`cv2.getNumThreads()` 与配置一致；fraction 生效。

## 2. 接入现有脚本

- [ ] 2.1 `scripts/label_gate_native.py`：默认 `--min-free-mib 12000 --max-util 15 --yield-interval 60 --max-gpu-fraction 0.35`，接 L1/L2/L3/L4。
- [ ] 2.2 `scripts/recheck_gate_dog_labels.py`：同上（帧数少但同样是 4K 解码）。
- [ ] 2.3 `scripts/train_gate.py`：接 L1/L2/L4，`num_workers` 默认降到 2，加 `--max-gpu-fraction`。
- [ ] 2.4 `scripts/checks/gpu_watcher.py`：新增 `--monitor-during-run <pid>`，运行中恶化则 `SIGSTOP`。

## 3. 演练（必须真跑）

- [ ] 3.1 预检拒绝演练：占 12 GB 后跑 `--limit 1` → 退出码 3 + 原因表。
- [ ] 3.2 运行时让行演练：开跑后插入占用 → ≤60 s 内 yield 暂停；撤掉后恢复。
- [ ] 3.3 限额验证：线程数/显存峰值符合配置。
- [ ] 3.4 产物：`results/gate/guard_drill/{preflight_refuse,yield_pause,limits}.log`。

## 4. Skill 与文档

- [ ] 4.1 新增 `.claude/skills/experiments/SKILL.md`：实验前 checklist（资源预检/预算/预计耗时/回滚）、运行中让行协议、产物与 run registry、事故表。
- [ ] 4.2 `remote-server-discipline` 翻车案例表补一条：本次 load 103 + frp 掉线 + 脚本无护栏。
- [ ] 4.3 `remote-servers` §5 GPU 纪律补「代码级护栏：resource_guard 默认开启」。

## 5. 复盘与验收

- [ ] 5.1 用护栏重跑一次门控标注剩余帧，记录资源轨迹（峰值显存/load/让行次数）与耗时对比。
- [ ] 5.2 用户验收：护栏默认参数是否合适（阈值/暂停策略），确认后固化。
