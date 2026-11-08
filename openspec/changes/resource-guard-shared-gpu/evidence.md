# 证据

## 只读核查及任务修订待确认

- 子代理对 `resource_guard.sh`、`remote_run.sh`、`_remote_common.sh` 执行 `bash -n` 通过。既有 `tests/test_resource_guard_process_tree.py` 两次运行均 2 failed；未改原有未提交 patch，未运行 GPU、远程或 12GB 演练。
- 父复核纠正：`test_tree_pids_includes_grandchildren` 在等待 writer 之前读取文件，`FileNotFoundError` 发生在调用 guard 之前，存在测试竞争，不能判定 guard 树遍历故障。stat 测试直接执行 sed+awk 而未调用 guard，fixture 输出 23、期望 27，不能证明生产 parser 故障；原因未确认，不作归因。`pet-pipeline/evidence.md` 历史记录把两项失败归因未提交 patch，证据不足，以此更正为准。
- 首次 pytest 使用系统临时目录及 `junit.xml`，偏离项目 fixtures 路径规则；第二次临时目录及 `junit-results-tmp.xml` 放在 `results/tests/resource-guard-readonly/`。未删除其他会话数据。
- D6 已定超限终止并记录采样日志，旧 proposal/spec 和 tasks 仍要求 SIGSTOP/恢复，合同冲突；不能按旧危险演练执行。最小修订待用户确认：统一终止义务与日志证据边界，安全短 CPU 验证不能替代 GPU/共享机实证；不复制已有单数 experiment skill 为复数、不重跑 12GB。1.3、4.2 内容虽已有，未核对完整顺序前不勾，不能越过前面未完项。
