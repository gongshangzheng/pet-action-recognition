# Design: resource-guard

## D1 事故事实（先量化，再设计）

| 项 | 观测 |
|---|---|
| 触发任务 | `label_gate_native.py --tiles 3` 全量 15,139 帧（每帧 cv2 解 2880×1620 HEVC + 9 次 GDINO 前向） |
| 主机负载 | load average 68.6 / 103.6 / 72.3（1/5/15 分钟均值），16 用户在线 |
| 连带故障 | frp 隧道两度中断；一次 `Connection refused` 持续 >10 min；期间 SSH banner 超时 |
| 我的脚本护栏 | **0**：无他人进程检测、无线程上限、无显存上限、无运行时复查 |
| 现行 skill | 仅人工纪律（跑前 `nvidia-smi`），无代码机制 |

## D2 四层护栏

### L1 预检（fail-fast，默认拒绝）

```
条件（全部满足才允许开跑）：
  free_mib(target_gpu) ≥ --min-free-mib      (默认 12000)
  util(target_gpu)     ≤ --max-util          (默认 15)
  他人计算进程数         == 0                 (nvidia-smi --query-compute-apps，排除自身)
  load1               ≤ --max-load          (默认 = 2 × CPU 核数 × 0.5)
  可用内存             ≥ --min-free-mem-gb   (默认 8)
  free_disk(results)   ≥ --min-free-disk-gb  (默认 20)
不满足 → 打印**拒绝原因表**并以退出码 3 结束（不是警告后继续）。
```

`--force` 允许越过，但必须同时给 `--force-reason`，并写进资源轨迹（便于事后追责与复盘）。

### L2 运行时限额（默认保守）

| 项 | 默认 | 理由 |
|---|---|---|
| `torch.set_num_threads` | `min(4, cpu/4)` | 解码/预处理并行度不需要吃满全机 |
| `OMP_NUM_THREADS` / `MKL_NUM_THREADS` | 同上 | 避免 OpenMP 线程风暴 |
| `cv2.setNumThreads` | 2 | 每 worker 2 线程足够 4K 解码 |
| DataLoader `num_workers` | ≤ 4 | 训练时并行读盘上限 |
| `torch.cuda.set_per_process_memory_fraction` | 0.35（24 GB 卡 ≈ 8.4 GB） | 留足共享余量，OOM 变成自己失败而不是连累别人 |
| 进程优先级 | `nice -n 10`（脚本自降） | 他人任务优先 |

### L3 合作式让行（yield）

每 `--yield-interval` 秒（默认 60）复查一次：

```
他人计算进程出现 或 显存被占 > 阈值 或 load1 超阈
   → 写一条 yield 事件到资源轨迹
   → 暂停：默认 --yield-action pause（自己 SIGSTOP，条件恢复后 SIGCONT）
     可选 --yield-action exit（保存进度后退出，退出码 4）
```

**为什么是暂停而不是硬扛**：共享机的礼貌不是"我快跑完"，而是"我能让就让"。暂停不丢进度，恢复代价小。

### L4 资源轨迹（可审计）

`results/<task>/resource_trace.jsonl` 每行：`{ts, stage, gpu_index, used_mib, util, load1, free_mem_gb, threads, event}`；结束写 `resource_summary.json`（峰值/均值/让行次数）。没有轨迹的实验视为未记录实验。

## D3 与 gpu_watcher 的分工

- `gpu_watcher.py`：**点火前**等待空闲（已有）；
- `resource_guard`：**开跑时**再验一次（避免 watcher 与启动之间的竞态），并在**运行中**持续复查。
- watcher 增加 `--monitor-during-run <pid>`：对已启动任务做运行中监控，条件恶化时发 `SIGSTOP`。

## D4 演练与验收（必须做，不能只写文档）

1. **预检拒绝演练**：在 GPU0 上起一个小占用进程（`torch.zeros` 占 12 GB），跑 `label_gate_native --limit 1` → 必须以退出码 3 拒绝并打印原因表。
2. **运行时让行演练**：正常开跑后，60 s 内插入占用进程 → 必须出现 `yield` 事件并暂停；撤掉后恢复。
3. **限额生效验证**：脚本内 `torch.get_num_threads()` 必须等于配置值；`nvidia-smi` 观测显存峰值 ≤ 设定的 fraction。
4. 三次演练的日志与轨迹入 `results/gate/guard_drill/`。

## D5 不做

- 不做全局调度器/队列系统（超出一个 skill + 一个模块的范围）；
- 不接管他人的进程（永不 `kill` 非本进程）；
- 不在离线（无 GPU）路径上加护栏，避免污染纯 CPU 的单元测试。

## D6 方案修订（2026-10-29，用户指出 CyberVerse 已有同款机制）

用户提示 `~/code/CyberVerse/.agents/skills/` 下有成熟实现，经核对后**改为移植而非自研**：

| CyberVerse 资产 | 作用 | 本仓处置 |
|---|---|---|
| `remote-ops/scripts/resource_guard.sh` | `preflight`（GPU 显存持有量 ≥500 MiB 判忙 / load per-core / mem / disk）+ `run`（nice + 线程上限 + CPU/RSS/显存/时长看门狗，超限 TERM→KILL） | **原样移植**（仅改磁盘检查层级与默认 GPU 索引） |
| `remote-ops/scripts/remote_run.sh` | 用 ssh 把 resource_guard 管道过去执行任意命令 | **原样移植**（改 REMOTE_ROOT/环境变量名） |
| `remote-ops/scripts/code_audit.py` | 静态扫描内存炸弹写法 + `smoke` 降规模测峰值 RSS | **原样移植** |
| `remote-ops/SKILL.md` | 三道闸、退出码表、GPU 判忙口径 | 重写为本仓版本（pet / plf / 2×4090 / 数据路径 / 无代理） |
| `experiment/SKILL.md` | 实验方法论（change 先行、evidence.md、留痕、回滚） | 移植精简版（下一步） |

**放弃**自研的「L3 合作式让行（SIGSTOP 暂停）」：CyberVerse 的做法是**超限直接终止 + 留采样日志**，
更简单、不会留下半死不活的暂停进程；让行改由「预检拒绝 + 运行中看门狗」覆盖。
保留自研的「资源轨迹」要求（`resource_guard` 的采样日志已满足，落盘位置按本仓 `results/` 约定）。
