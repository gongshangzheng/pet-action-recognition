# Proposal: 共享机资源护栏

## Why

门控标注曾造成共享机负载升高和连接中断。运行前检查、运行时终止超限进程以及日志可降低风险，但不能保证瞬时不超限或其他用户绝不受影响。

## What Changes

按已确认的 D6，以现有 `remote-ops` 护栏为基础核对预检、运行时限额和采样日志。先核对实现和调用入口，再验证短 CPU 真实进程的拒绝、超限退出和进程树停止；GPU 与共享机验证须另获资源预检和执行授权，不用 CPU 结果代替。取消暂停/恢复、12 GB 占用演练和复数 experiments skill。保留已有单数 experiment skill。

## Capabilities

### New Capabilities

- `resource-guard`: 共享机运行前预检、超限终止与可审计日志。

## Impact

涉及现有 remote-ops 护栏、调用入口、测试及相关纪律文档。旧任务逐号处置见 `task-map.md`。本 change 不要求重跑门控标注，也不接管其他用户进程。
