# Tasks: resource-guard-shared-gpu

编号是执行顺序；未标明并行的任务严格串行。旧号及取消理由见 `task-map.md`。若需要修改已有用户未提交的 `resource_guard.sh`，停止并请父审阅、单独授权原 patch 的处置。

## 1. 已有移植与核对

- [x] 1.1 移植 `resource_guard.sh` / `remote_run.sh` / `_remote_common.sh` / `code_audit.py` 到 `.claude/skills/remote-ops/scripts/`（改磁盘检查层级、默认 GPU 索引、REMOTE_ROOT、无代理）。
- [x] 1.2 写本仓版 `remote-ops/SKILL.md`：三道闸、退出码表、GPU 判忙口径（≥500 MiB 显存持有）、`setsid` 纪律、连 pet 不走代理。
- [x] 1.3 核对当前护栏实现的预检、限额、退出码和日志；判据：逐项对照及差异写入 evidence。
- [x] 1.4 修正 `remote_run.sh` 捕获预检失败码；判据：通过调用生产 `remote_run.sh` 的回归测试，预检返回 2/3 时入口分别返回原码，且任务 marker 不生成。测试只用隔离目录中的生产 `remote_run.sh` 和 `_remote_common.sh` symlink 与 preflight/ssh stub，stub 不复制生产逻辑且不执行 SSH。
- [x] 1.5 核对现有调用入口是否按共享机纪律使用护栏；判据：入口清单及缺口写入 evidence。
- [x] 1.6 核对 `remote-server-discipline` 对 remote-ops 的引用与事故记录；判据：核对结果及必要修订写入 evidence。

## 2. 短 CPU 验证

- [ ] 2.1 修正现有进程树测试的 writer 等待竞态及 fixture，使测试调用生产护栏；判据：测试代码和执行结果可复核，不以独立 sed/awk 结果冒充生产证据。
- [ ] 2.2 验证短 CPU 真实进程预检拒绝；判据：记录拒绝原因、退出码和子任务未启动的证据。
- [ ] 2.3 验证短 CPU 真实进程超限退出及日志；判据：记录限额、退出码和关联日志。
- [ ] 2.4 验证超限时受控进程树停止；判据：记录父子进程退出的证据。

## 3. 文档与真实环境验收

- [ ] 3.1 核对远程纪律事故记录；判据：事故条目及核对结果写入 evidence。
- [ ] 3.2 核对 remote-servers 文档与当前护栏调用约定；判据：文档及核对结果一致，不声称所有入口已自动接入。
- [ ] 3.3 用户确认真实 GPU 与共享机最小安全验证范围和执行授权；判据：授权、范围和资源预算写入 evidence。
- [ ] 3.4 在通过资源预检后执行获批的 GPU 预检验证；判据：结果与日志写入 evidence，不使用 12 GB 占用演练。
- [ ] 3.5 在通过资源预检后执行获批的共享机验证；判据：结果、限制与日志写入 evidence，不以 CPU 验证冒充。
- [ ] 3.6 用户确认护栏阈值及验收结论；判据：决定与剩余风险写入 evidence。
