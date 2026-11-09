# 证据

## 只读核查及任务修订

- 子代理对 `resource_guard.sh`、`remote_run.sh`、`_remote_common.sh` 执行 `bash -n` 通过。既有 `tests/test_resource_guard_process_tree.py` 两次运行均 2 failed；未改原有未提交 patch，未运行 GPU、远程或 12GB 演练。
- 父复核纠正：`test_tree_pids_includes_grandchildren` 在等待 writer 之前读取文件，`FileNotFoundError` 发生在调用 guard 之前，存在测试竞争，不能判定 guard 树遍历故障。stat 测试直接执行 sed+awk 而未调用 guard，fixture 输出 23、期望 27，不能证明生产 parser 故障；原因未确认，不作归因。`pet-pipeline/evidence.md` 历史记录把两项失败归因未提交 patch，证据不足，以此更正为准。
- 首次 pytest 使用系统临时目录及 `junit.xml`，偏离项目 fixtures 路径规则；第二次临时目录及 `junit-results-tmp.xml` 放在 `results/tests/resource-guard-readonly/`。未删除其他会话数据。
- D6 已定超限终止并记录采样日志，旧 proposal/spec 和 tasks 仍要求 SIGSTOP/恢复，合同冲突；不能按旧危险演练执行。用户已确认按 D6 修订：统一终止义务与日志证据边界，安全短 CPU 验证不能替代 GPU/共享机实证；不复制已有单数 experiment skill 为复数、不重跑 12GB。1.3、4.2 内容虽已有，未核对完整顺序前不勾，不能越过前面未完项。

## 2026-11-08：1.3 护栏实现核对（本机静态核查）

### 生产实现对照

- `resource_guard.sh preflight`：快照后拒绝无法取得 GPU 清单（rc 1）；compute-apps 持有量 ≥500 MiB 判忙，或 util/mem 比例过阈判忙（rc 2）；load/core、可用内存、checkout 磁盘压力用 rc 3 表示。默认阈值：GPU util 50%、显存比例 80%、load/core 0.7、available memory 8000 MiB、磁盘 5 GB；`--allow-busy-gpu` 可降级忙卡拒绝为 warning，与 change 的“不得以绕过选项规避共享机纪律”要求不一致，应由后续任务审定，不在本轮改实现。
- `resource_guard.sh run`：默认 GPU index 0、GPU 90%、CPU 350%、进程树 RSS 24000 MiB、超时 3600 秒、采样间隔 5 秒、线程 8、nice 10；通过进程组采样、超限 TERM 后最多等待约 12 秒并 KILL，cap breach rc 4；命令自身成功 rc 0、失败 rc 5。日志以 append 写入 `--log` 或 `.run/guard/run-<timestamp>.log`，含命令、限制、定期间隔采样及 `CAP BREACH` 原因；正常结束记录命令返回码。限额是采样触发而非瞬时硬限制。
- `remote_run.sh` 默认自动调用 `preflight.sh`，`--skip-preflight` 可显式绕过；此接口与本 change 的共享机“不绕过”要求存在差异。`preflight.sh` 保留守卫 rc 2/3，远端 SSH 失败映射为 1。
- **实际阻断缺陷（远程入口退出码）**：`remote_run.sh:45-49` 写作 `if ! bash ...; then rc=$?`。在失败分支中 `$?` 是 `!` 反转后条件命令的状态 0，不是 preflight 原退出码；因此拒绝启动分支会打印“退出码 0”并 `exit 0`。最小复现 `bash -c 'if ! false; then rc=$?; printf "captured=%s\\n" "$rc"; fi'` 输出 `captured=0`。影响 1.3 的退出码传递核对及 remote_run 调用者对拒绝结果的判断；虽任务命令未被执行，但调用方会把拒绝误认成成功。最小修复方向：在未反转的条件分支捕获真实状态（例如 `if bash ...; then :; else rc=$?; ...; fi`），并新增/调整一个以可替换本地 preflight 命令或 shell fixture 验证“拒绝时命令不执行且 remote_run 返回原拒绝码”的回归判据。**本轮未改 `remote_run.sh`，也未新增任务结构；修复需父审阅任务拆分/批准后实施。**
- 守卫依赖 Linux `/proc`、`nvidia-smi` 及 Bash associative arrays（Bash 4+）；本机是 macOS，虽 `bash -n` 语法核查通过，但本机不构成 Linux `/proc` 进程树真实终止验证。不得把 CPU/macOS 静态核查写作 Linux 进程终止或 GPU/共享机实证。

### 既有测试复核

- 命令：`python3 -m pytest tests/test_resource_guard_process_tree.py -q --basetemp=results/tests/resource-guard-worker-20261108 --junitxml=results/tests/resource-guard-worker-20261108/junit.xml`；结果 **2 failed**。结果目录位于项目 `results/tests/`，未用系统临时目录。
- `test_tree_pids_includes_grandchildren` 原文错误为 `FileNotFoundError`，发生在 `pid_file.read_text()`，在调用 `resource_guard.sh tree-pids` 前；子进程 writer 尚未写入 pid 文件，是测试等待竞态，不能归因 guard。
- `test_cpu_stat_parser_handles_spaces_in_process_name` 只对 fixture 文件执行 `sed`/`awk`，没有调用生产 guard；fixture 字段得到 `23`、测试期望 `27`。这只说明该测试自身的字段索引/期望不符，不能证明生产 parser 故障。
- `bash -n .claude/skills/remote-ops/scripts/{resource_guard.sh,remote_run.sh,_remote_common.sh}` 等价逐文件语法检查通过（macOS GNU Bash 5.3.9）。未执行远程、GPU 或真实 Linux `/proc` 终止测试；未修改 guard 源码。

### 1.3 状态

实现与差异核查证据已记录。父审阅允许仅按审计完成勾选 1.3；此前编号 1.1/1.2 均已完成。发现 `remote_run.sh` 把预检拒绝误报为 rc 0，因此此勾选不表示该实现缺陷已修复，当前队列在此暂停：不开始 1.4，不改源码，不新增 task 结构，等用户确认最小修复的任务拆分方案。既有两项 pytest 失败与此修复无关，不作为前置或顺带修复目标。

### 1.4 批准范围与 RED/GREEN 核验（已完成；等待后续任务顺序推进）

- 用户批准在 1.3 后插入 **1.4 修正 `remote_run.sh` 预检失败码**；原 1.4/1.5 顺延为 1.5/1.6，其他 2.x、3.x 编号及任务保持不变。映射记录见 `task-map.md`。1.3 由逐项实现核查及差异写入本 evidence 支持完成；该勾选只表示核查完成，不表示所有实现均无缺陷。
- 最小复现：`bash -c 'if ! false; then rc=$?; printf "captured=%s\\n" "$rc"; fi'` 输出 `captured=0`。生产 `remote_run.sh` 的 `if ! bash ...; then rc=$?` 因此将 preflight 的拒绝状态错误报告为成功码 0。影响 task 1.3 核对出的退出码传递及远程入口拒绝结果契约。
- 获批修改范围：仅用未取反条件分支捕获原始 preflight 返回码；增加真正调用生产 `remote_run.sh` 的回归测试，验证 preflight 拒绝码 2/3 被入口原样返回且实际 marker 命令未启动。测试 fixture 在 `results/tests/` 下隔离，使用生产 `remote_run.sh`/`_remote_common.sh` symlink；本地 preflight stub 只替代远程资源检查，PATH 中的 ssh stub 只用于确认未触发 SSH，不进行网络访问。不添加 production fallback/配置点；不触碰 `resource_guard.sh`、skip-preflight、进程树、默认阈值及既有两项失败测试。
- 测试先因 `text=True` 严格 UTF-8 解码生产中文 stderr 失败（`UnicodeDecodeError`），这是测试 harness 问题，不是有效 RED；调整为替换非法字符解码后，`results/tests/remote-run-preflight-evidence/red-confirmation.txt` 记录有效 RED：两例均断言入口码时失败，实际返回 0（预期分别 2、3）。之后只改生产逻辑为未取反条件分支捕获原始退出码。
- GREEN：`results/tests/remote-run-preflight-evidence/green.txt` 及最终复跑 `final.txt` 均为 2 passed；测试确认拒绝码 2/3 原样返回，任务 marker 与 SSH marker 均未创建。`bash -n .claude/skills/remote-ops/scripts/remote_run.sh` 与目标文件 `git diff --check` 通过。父独立复跑测试 2 passed 及 bash-n 并批准勾选 1.4。
- 未运行 SSH、GPU、模型、安装依赖或远程任务。未完成 Linux/GPU/共享机真实验收；本证据仅验证本地生产入口对预检拒绝的退出码传递及不启动行为。后续编号从 1.5 开始，当前工作按父要求暂停，不继续 1.5。

## 2026-11-08：1.5 现有调用入口审计（静态核查）

### 审计范围与判定口径

只核对当前正式门控GPU入口、仓库中存在的远程启动封装、GPU watcher，以及证据/脚本能明确指向的调用关系；不以出现 guard 名称或 GPU busy 查询等同于完整受控，不要求把 guard 内嵌所有脚本。入口分类：直接使用生产 remote-ops 护栏、需要调用者外部包装、或当前实际入口存在绕过/未确认检查。未执行训练、推理、SSH 或远端命令。

### 门控及GPU入口清单

- `scripts/label_gate_native.py`：脚本自身没有 preflight、`remote_run.sh` 或守卫调用。CLI docstring 是裸 `python scripts/label_gate_native.py ... --device cuda:0` 示例。它是GPU模型推理/视频解码入口，应由远程调用方先做容量预检并以 `remote_run.sh` 包装；**源代码不直接受控，裸执行会绕过**。仓库内没有找到当前可执行调用器。`openspec/changes/presence-gate-model/evidence.md` 及 task 0.4 记录了 2026-10-27 watcher曾经点火跑该脚本，但该历史记录没有给出 `--on-free` 命令，不能证明点火时有 remote_run/preflight/guard。
- `scripts/recheck_gate_dog_labels.py`：与上项相同，CLI 用法是裸 Python + `--device cuda:0`；自身不做资源检查或守卫。`tmp/poll_until_connected.sh` 中一条现存示例通过 SSH 用 `setsid nohup ... < /dev/null` 启动该脚本，保证会话脱离与 stdin 关闭，但该执行命令没有 preflight 或 resource guard；这是**可见的绕过/缺检查调用**，并且脚本位于用户未跟踪 `tmp/`，本审计未修改。
- `scripts/train_gate.py`：可选设备默认自动选 `cuda:0`，脚本内有线程/worker限制但没有容量预检或 resource guard；CLI 是裸 Python 示例。应由调用者在远程先 preflight、再经 `remote_run.sh` 包装。未发现当前仓库内正式调用器，不能把线程上限当作GPU共享机护栏。
- `scripts/checks/gpu_watcher.py`：仅用 `nvidia-smi` 检查可用显存与利用率，默认要求显存空闲≥12000 MiB、利用率≤15%、连续3次；不同于护栏按进程显存持有和系统资源做的 preflight，也不施加CPU/RSS/GPU/时长限制。`--on-free` 使用 `subprocess.run(..., shell=True)` 执行任意命令，虽设 `stdin=DEVNULL`、日志和超时仅约束 watcher 自身，不保证子命令受守卫；若点火GPU任务，命令必须显式走 remote-ops。当前任务文档只保留旧 watcher 运行记录，没保存点火命令，因此历史真实启动是否包装**无法核实**。

### 当前远程启动封装与默认预检

- 正式入口 `.claude/skills/remote-ops/scripts/remote_run.sh` 默认 `SKIP_PREFLIGHT=0`；它先调用同目录生产 `preflight.sh`，仅成功后才 SSH 并把 `resource_guard.sh` 经 stdin 送远端执行 `run`。`--gpu-index` 会同时传给 preflight 和远端 guard。1.4 的生产入口回归测试证明 preflight 返回2/3时原码向上传播、任务和SSH marker均不生成。因而**通过 remote_run 的命令默认有预检并受远端运行守卫约束**。
- 该入口仍接受 `--skip-preflight`，可由调用者显式跳过本机发起的预检；本次未移除/改动该参数。审计找到的项目级 `remote_run.sh` 调用证据均没有显示使用该选项，但不能由此证明不存在其他人工/仓外调用。直接 SSH、裸远端命令，以及别的 watcher shell 命令都不继承 remote_run 默认预检。
- 四个已有正式封装 `scripts/remote/run_clip_training.sh`、`run_clipv9_training.sh`、`render_clip_windows.sh`、`run_missing_detection.sh` 均直接调用 `bash scripts/remote/resource_guard.sh run ...`。但仓库中 `scripts/remote/resource_guard.sh` 不存在且不受 Git 跟踪；生产护栏实际位于 `.claude/skills/remote-ops/scripts/resource_guard.sh`。因此这些封装**不能据现状认定为有效的直接受控入口**，若按仓库当前文件执行会在 guard 调用处失败；它们也没有调用 remote-ops `preflight.sh`。本轮仅登记缺口，不修复路径或改变接线。
- 可确认直接走生产守卫的本仓操作证据：`openspec/changes/presence-gate-model/evidence.md` 记录 `train_gate_video.py` 训练/评估命令经 `.claude/skills/remote-ops/scripts/remote_run.sh` 执行，并记录预检通过；其他 experiment evidence 也有 `remote_run.sh` 受控任务实例。这证明该接口可供外部包装使用，不证明上述三个门控入口均已接线。
- 其他旧的脚本/实验文档含 `nohup`、裸 `nvidia-smi` 检查等历史内容；本次不对全仓脚本逐一展开扫描或判定，除上述可识别正式入口外均为未审范围。

### 后台 stdin / session 纪律

`remote-ops/SKILL.md` 明确禁止单次 SSH 中 `nohup ... & disown`，要求 `setsid nohup` 或由 `remote_run.sh` 托管；项目 `AGENTS.md` 进一步要求远程后台命令显式 `</dev/null`。上述 `tmp/poll_until_connected.sh` 示例使用 `setsid nohup` 且 `< /dev/null`，符合后台 session/stdin 纪律，但仍缺资源预检及任务守卫。gpu_watcher本身的 `on-free` 子命令 stdin为DEVNULL，不等于后台脱离调用方或资源受控。

### 覆盖边界与结论

本清单覆盖三项被指定审计的门控入口、watcher、当前仓库四个 `scripts/remote/` guard封装、remote_run生产入口和一条明确的 recheck后台调用。未覆盖所有实验历史命令、仓外调用、远程当前文件状态或 watcher当时传入的 `--on-free` 参数。现有入口状态不是“guard all pass”：脚本级门控入口需外部包装；存在可见的裸调用/预检缺失；四个旧封装引用不存在的guard路径；remote_run默认预检有效但存在skip参数。入口审计按判据完成，接线义务未取消也未在此实现；task-map中旧接入缺口仍待后续决定。当前按顺序的首未完成任务仍为1.5的父审阅/放行；经父确认后方可勾选1.5并开始1.6，不能据本段直接勾选或越项执行。

## 2026-11-09：1.6 remote-server-discipline 引用与事故记录核对

只读核对 `.claude/skills/remote-server-discipline/SKILL.md`，未执行远程命令。

### 一致项

- §5 把预检/守卫/看门狗/静态审计的唯一出处指向 `remote-ops` skill；引用的 `resource_guard.sh preflight --gpu-index N`、`remote_run.sh` 与退出码 2（容量被占 → 停下来问用户）与生产脚本一致。
- 事故记录「2026-10-27/28 门控标注把 load 顶到 103、frp 隧道两度中断」与 `remote-ops` SKILL 开头的同一事故描述一致，两处不冲突。

### 差异及已做修订

- §0 声称 `servers.yaml`（本 skill 目录下）是服务器唯一信息源，但 `.claude/skills/remote-servers/` 只有 `SKILL.md` 与 `scripts/`，`servers.yaml` 不存在（全仓 `rg -l 'servers.yaml'` 仅命中本文件）。改为指向 `remote-servers` skill 与 `remote-ops` 环境契约表两处实际材料。
- §6「`scp` 到远程 `/tmp/`（一次性）」与项目 `AGENTS.md` 冲突：远程临时产物只进仓库 `tmp/`，不放系统 `/tmp` 或 `$HOME` 根目录；可复用脚本必须先进仓库。改为先进仓库再推送，一次性探针放远程 `tmp/`。
- §5 未提绕过选项，补一条：共享机上禁止用 `--allow-busy-gpu`、`--skip-preflight` 规避预检。这与本 change 的「不得以绕过选项规避共享机纪律」一致；选项本身仍留在脚本里，本轮不改脚本。

### 未处理

`--allow-busy-gpu`（preflight/guard 均接受）与 `remote_run.sh --skip-preflight` 仍是脚本级 bypass 能力，本轮只在纪律文档层面禁止使用，未删除参数；如需强制，得另立任务改脚本（`resource_guard.sh` 还有用户未提交 patch，不在本任务范围）。
