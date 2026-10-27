## ADDED Requirements

### Requirement: 可核验的独立迁移

迁移 SHALL 在课题组服务器新增独立项目目录，保留项目源码、恢复的猫视频和
原始标注、OpenSpec 与研究报告，并逐文件核对大小与 SHA-256。迁移 SHALL
排除本机凭据及 Windows 运行环境，不覆盖现有实验项目。

#### Scenario: 迁移成功

- **WHEN** 本机源可读、目标容量和传输通道可用
- **THEN** 新项目包含代码、2,737 个正常视频及原标注，清单逐项校验通过

#### Scenario: 中断后续传

- **WHEN** 大文件上传或 SSH 中途断开
- **THEN** 保留可恢复的临时状态，已校验文件跳过，坏文件不冒充完成

### Requirement: 训练来源可迁移

迁移 SHALL 提供 Linux 本机地址版及相对路径版标注，保留原始 Label Studio
帧区间语义，并明确默认整视频单标签入口不能直接使用该标注。

#### Scenario: 地址迁移

- **WHEN** 本机副本含 Windows 绝对路径
- **THEN** 在服务器生成对应 Linux 路径副本，原始和相对版内容保持不变
