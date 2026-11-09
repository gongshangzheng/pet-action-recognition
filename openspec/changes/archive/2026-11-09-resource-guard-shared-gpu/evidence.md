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

## 2026-11-09：2.1 进程树测试去竞态并改跑生产护栏

- 代码：`tests/test_resource_guard_process_tree.py`（commit `0d61179`）。
  - `tree-pids` 测试先等待 writer 写入两个 pid 再调用生产 `resource_guard.sh tree-pids`，消除「调用 guard 前读文件」的竞态。
  - 删除伪造 `/proc/<pid>/stat` fixture 与独立 `sed`/`awk` 断言（原 fixture 字段位置错位，输出 23 期望 27）。改为 Linux 上真实进程验证：把 `/bin/sh` 复制成 `worker pool`（comm 含空格），交给生产 `resource_guard.sh run --max-cpu-pct 20 --interval 1` 跑，断言返回 4 且日志含 `CAP BREACH` 与 cpu 原因。解析若错位就不会判超限，该断言会真的失败。
- 本机（macOS，无 `/proc`）：`1 passed, 1 skipped`，证据 `results/tests/resource-guard-task-2-1/`。
- pet（Linux，经生产 `remote_run.sh` 守卫执行）：`2 passed in 13.18s`，即两条测试都真正跑过生产护栏。
- 说明：外层守卫采样显示 `cpu=0%`，因为内层测试自己又起了一个守卫把 burner `setsid` 到新会话/进程组，外层按 ppid 树看不到它。这是嵌套守卫的采样盲区（committed 版按 ppid 树、本地未提交 patch 改为按进程组），不是本次测试失败。

## 2026-11-09：2.2 短 CPU 真实进程预检拒绝

判据：拒绝原因、退出码、子任务未启动。真实远端资源、真实进程，未用 stub，未跑 GPU。

- 用例 A（磁盘阈值）：`preflight.sh --min-free-disk-gb 999999` → **返回 0 且 PREFLIGHT OK，没有 disk 行**。核查发现 `resource_guard.sh` 的 disk 判定写作 `disk_gb=$(df -Pk ... | awk 'NR==2{int($4/1048576)}')`，awk 只求值不打印，`disk_gb` 恒为空，`[[ -n "$disk_gb" ]]` 直接跳过比较 → **磁盘超限闸门是死的**。该用例不能作为拒绝证据。
- 用例 B（load 阈值，有效）：`preflight.sh --max-load-per-core 0.001`（24 核 → 限制 0.02，真实 load 0.57/0.48）→ `CPU pressure: load 0.57 > 0.02`，退出码 **3**。
- 子任务未启动：同一预检以 `&&` 串接 `ssh pet 'touch tmp/preflight-refused-marker'`，链返回 3，远端 marker 不存在。remote_run 内部「预检非零即不启动任务」的传递另由 1.4 的生产入口回归测试覆盖。
- 证据：`results/tests/resource-guard-2-2/refusal.txt`。发现（a）在 pet 上直接跑 `preflight.sh` 不可用，它自己再 `ssh pet`，远端没有该别名，返回 1——该脚本只能本地发起，文档已如此写，但脚本自身没有防呆。

## 2026-11-09：2.3 短 CPU 真实进程超限退出及日志

- 命令（本地发起，走生产 `remote_run.sh`，自动预检通过）：`--max-cpu-pct 20 --interval 1 --timeout-s 30 --log tmp/guard/cpu-breach.log -- bash -c 'while :; do :; done'`
- 结果：`remote_run.sh` 退出码 **4**；守卫采样 `cpu=101%`，日志含 `CAP BREACH (cpu 101% > 20%): terminating 144822`，头部记录 `# command:` 与 `# caps: gpu0<=90% cpu<=20% rss<=24000MB timeout=30s threads=8`。
- 证据：`results/tests/resource-guard-2-3/run.txt`。日志落在远端 `tmp/guard/`（未写入系统 `/tmp`）。

## 2026-11-09：2.4 超限时受控进程树停止

- 命令：`remote_run.sh --max-cpu-pct 60 --interval 1 --timeout-s 30` 跑 `bash -c 'echo $$ > tmp/guard/parent.pid; for i in 1 2 3 4; do (while :; do :; done) & echo $! >> tmp/guard/children.pid; done; wait'`
- 结果：退出码 **4**，采样 `cpu=406%` 触发 `CAP BREACH`；父进程 145536 与子进程 145540/145541/145543/145545 全部 `gone`；排除自匹配后远端无残留 busy loop。
- 证据：`results/tests/resource-guard-2-4/run.txt`。第一次残留计数为 3 是 `ps`/`grep`/`ssh` 自匹配，已按项目纪律改用 `grep -v` 排除后复核为 `none`。
- 边界：committed 版按 ppid 树终止即可覆盖同组子进程；本地未提交 patch 改为按进程组，本轮未验证该 patch 版本。

## 2026-11-09：3.1 远程纪律事故记录核对

- `.claude/skills/remote-server-discipline/SKILL.md` §8 六条事故逐条核对：2026-10-27/28 门控标注 load 103、frp 隧道中断一条在 §5 与 `remote-ops` SKILL 开头两处一致；其余（A100 未经批准装环境、脏工作树反复拒 push、tar CJK 文件名、heredoc 引号、replace 未验证、plf `-q` 静默失败）无法从当前仓库复核发生过程，按历史记录保留。
- 修订 1：`ssh heredoc 语法错误` 的修正列原写「脚本本地写好 scp」，与 1.6 修好的 §6 及项目 `AGENTS.md`（脚本先入库再 push，`/tmp` 不放脚本）冲突，改为「脚本先入库再 push，不靠 scp」。
- 修订 2：§8 补一行记录门控标注事故，使事故表覆盖本 skill §5 引用的那一起。
- 修订 3（跨文档归因更正）：`openspec/changes/pet-pipeline/evidence.md` 原把两条 `test_resource_guard_process_tree` 失败归因于工作区未提交的 `resource_guard.sh` 改动；2026-11-08 的复核表明是测试竞态与 fixture 字段错误，与 patch 无关。已在该行就地更正并指向本 change 的 evidence，未改写其他内容。

## 2026-11-09：3.2 remote-servers 文档与护栏调用约定核对

- `.claude/skills/remote-servers/SKILL.md`「GPU 共享」原写「跑前先 `nvidia-smi` 看卡空不空」，与 `remote-ops` 的判忙口径（看进程实际持有的显存，≥500 MiB 即忙，不看瞬时利用率）和退出码 2 处置冲突。已改为指向 `preflight.sh --gpu-index N`，并写清超过几秒的任务用 `remote_run.sh`。
- 同一节新增一句：各训练/评测入口**没有全部自动接护栏**，裸 `python scripts/xxx.py --device cuda:N` 会绕过预检与上限，需调用者在外部用 `remote_run.sh` 包装。这与 1.5 的入口审计结论一致，不声称所有入口已自动接入。
- 校验文档时把三处指向 skill 的 `[[training]]`/`[[testing]]`/`[[using-mmaction2]]` wiki 链接改成反引号 skill 名，避免被当成缺失文档。

## 2026-11-09：磁盘闸门修复（2.2 缺陷的处置）

用户授权改一行 `resource_guard.sh` 并复跑证据。实际改动两处，都只碰 disk 判定，不碰用户未提交的进程组 patch：

- `resource_guard.sh`：`awk 'NR==2{int($4/1048576)}'` → `awk 'NR==2{print int($4/1048576)}'`；检查对象 `$HERE/../../../..` → `${REMOTE_ROOT:-$PWD}`，使对象是 checkout 而不是按调用方式漂移的上级目录。
- `preflight.sh`：远端执行前 `cd '$REMOTE_ROOT'`，与 `remote_run.sh` 一致，否则从 `$HOME` 起算磁盘落在另一个文件系统。
- 修复后复跑：`--min-free-disk-gb 999999` → `disk pressure: 10381 GB free < 999999 GB`，退出码 **3**；默认阈值仍 `PREFLIGHT OK`，退出码 0。证据 `results/tests/resource-guard-disk-gate/disk-gate.txt`。
- 提交 `67f5ef1` 只含 disk 这两处；`resource_guard.sh` 用户未提交的进程组/setsid patch 仍在工作区，未纳入该提交（用 `git hash-object` + `update-index` 只提交修复后的 blob，未动工作区文件）。
- **残留事实**：checkout 所在 `/home` 是 `/dev/sda1`，可用 10.4 TB，默认 5 GB 阈值实际永远不会触发；磁盘闸门现在只是「能工作」，不是「能防住」。

## 2026-11-09：3.3 真实 GPU 与共享机验证的授权、范围与预算

用户当日确认最小范围，写入本 evidence 作为授权记录：

- 范围：① 一次只读的 GPU 预检（`preflight.sh` 读 `nvidia-smi` 状态，不申请显存）；② 一段秒级 CPU 任务经 `remote_run.sh` 作共享机验证。不做 12 GB 占用演练，不做显存占用、不跑训练/推理/模型。
- 资源预算：pet 上合计约 1–2 分钟、单核量级 CPU、无 GPU 显存占用；每次执行前先跑预检，预检不过就停。
- 未授权范围：任何占显存的 GPU 任务、并行压测、以其他用户身份的操作。

## 2026-11-09：3.4 GPU 预检验证（只读，不占显存）

- `preflight.sh --gpu-index 0 --json results/tests/resource-guard-3-4/gpu0.json`：`GPU 0 free: util 0%, mem 0%, held 0 MiB`，`PREFLIGHT OK`，退出码 **0**。
- `--gpu-index 1`：`GPU 1 free: util 0%, mem 0%, held 0 MiB`，退出码 **0**。
- 证据：`results/tests/resource-guard-3-4/gpu-preflight.txt` 和两个 json。
- 边界：验证的是「读到真实 GPU 状态并给出放行判定」这条路径，**没有**验证「有进程占显存时判忙返回 2」——那条需要真的占显存，按 3.3 授权未做。

## 2026-11-09：3.5 共享机上的守卫验证（正常完成路径）

- 命令：`remote_run.sh --max-cpu-pct 120 --max-rss-mb 2000 --timeout-s 30 --interval 2 --log tmp/guard/shared-ok.log -- /home/wyy/miniconda3/envs/plf/bin/python -c 'print(sum(range(20_000_000)))'`
- 结果：自动预检通过 → 退出码 **0**，输出 `199999990000000`，守卫记录 `command finished rc=0 in 2s`；日志头部含命令与 `caps: gpu0<=90% cpu<=120% rss<=2000MB timeout=30s threads=8`。
- 证据：`results/tests/resource-guard-3-5/run.txt`（含远端日志头尾）。
- 边界：这条补的是「限额内正常跑完也要留日志」这一半，与 2.3/2.4 的终止路径互补；它**不证明** GPU 行为、不证明其他用户完全不受影响，也不构成 12 GB 或并行压测结论。

## 2026-11-09：3.6 阈值与验收结论（用户确认）

用户当日指示「按最小范围跑，然后归档」，即接受以下结论后归档：

- 阈值保持默认、本次不改：预检 GPU util 50%、显存 80%、load 0.7/core、可用内存 8000 MiB、磁盘 5 GB；运行时 GPU 90%、CPU 350%、RSS 24000 MiB、超时 3600 s、采样 5 s、线程 8、nice 10。
- 验收口径：短 CPU 真实进程的拒绝（rc 3）、超限终止（rc 4）、进程树停止、日志齐备；GPU 只验证只读预检路径；共享机验证覆盖限额内正常完成。
- 剩余风险（一并归档）：
  1. 磁盘阈值在 10.4 TB 空闲的 checkout 上永不触发，磁盘闸门目前只是可用。
  2. 忙卡判定的拒绝路径（rc 2）未经真机验证，需要占显存才能验。
  3. nested 守卫盲区：外层按 ppid 树采样时看不到内层 `setsid` 出去的子进程（提交版即如此）；本地未提交 patch 改成按进程组，未纳入本轮验证。
  4. `--skip-preflight` 与 `--allow-busy-gpu` 仍属脚本级 bypass 能力，本轮只在纪律文档里禁止使用。
  5. 入口接线缺口（1.5）：`scripts/remote/` 下四个封装引用不存在的 `scripts/remote/resource_guard.sh`，门控脚本裸跑会绕过护栏；未修复。
  6. 用户未提交的 `resource_guard.sh` 进程组 patch 不在本轮验证范围内。
