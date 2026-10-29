## ADDED Requirements

### Requirement: 共享机任务必须通过预检

任何在共享 GPU/CPU 机器上运行的脚本 SHALL 在开跑前执行资源预检：目标 GPU 空闲显存与利用率、是否存在他人计算进程、主机负载、可用内存与磁盘余量。任一项不达标时脚本 MUST 拒绝开跑、打印具体原因并以非零退出码结束，MUST NOT 以告警形式继续执行。越过预检 SHALL 需要显式 `--force` 与书面理由，且该理由必须写入资源轨迹。

#### Scenario: 他人占用时拒绝开跑
- **WHEN** 目标 GPU 上存在他人计算进程或空闲显存低于阈值
- **THEN** 脚本拒绝启动并打印逐项原因
- **AND** 退出码非零，未执行任何推理或训练

#### Scenario: 强制越过需留痕
- **WHEN** 使用者以 `--force` 越过预检
- **THEN** 理由被写入 `resource_trace.jsonl`
- **AND** 报告中标注本次运行为强制越过

### Requirement: 运行时资源上限

脚本 SHALL 对 CPU 线程（torch / OpenMP / cv2）、DataLoader 并行度、进程优先级与显存占用设置上限；显存上限 SHALL 以进程级 fraction 形式设定，使自身超限时先自身失败而不影响同机其他任务。

#### Scenario: 线程与显存上限生效
- **WHEN** 脚本启动后读取自身配置
- **THEN** torch 与 cv2 的线程数等于配置值
- **AND** 进程显存峰值不超过设定的 fraction × 卡容量

### Requirement: 合作式让行

长时间运行的任务 SHALL 定期复查资源条件（默认间隔 60 秒）。当出现他人计算进程、显存被他人占用或主机负载超阈时，任务 MUST 让行：默认暂停自身并在条件恢复后继续，或保存进度后退出；两种行为 SHALL 各有对应的退出/恢复记录。

#### Scenario: 他人任务出现时让行
- **WHEN** 运行期间检测到他人计算进程或负载超阈
- **THEN** 任务在复查周期内让行（暂停或保存退出）
- **AND** 资源轨迹中出现 `yield` 事件

#### Scenario: 让行不破坏产物
- **WHEN** 任务从让行中恢复或按保存退出结束
- **THEN** 已完成的部分产物完整可读
- **AND** 未完成部分可区分（不产生半写文件）

### Requirement: 资源轨迹可审计

每次运行 SHALL 产出 `resource_trace.jsonl`（时间、阶段、显存、利用率、负载、线程数、事件）与结束时的 `resource_summary.json`（峰值/均值/让行次数）。未产出轨迹的运行 SHALL NOT 被记为有效实验证据。

#### Scenario: 报告可回溯资源代价
- **WHEN** 运行结束
- **THEN** 报告给出峰值与平均显存、利用率、负载以及让行次数
- **AND** 该轨迹可与产物目录一一对应
