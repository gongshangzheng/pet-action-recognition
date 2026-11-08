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
