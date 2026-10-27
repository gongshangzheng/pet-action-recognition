# rknn-simulator-feasibility Specification

## Purpose

通过小网络的实际构建与软件模拟核查 RV1126B 工具链的可行性，报告转换、初始化和推理各阶段结果，清理专用临时资源并避免将模拟结果外推到业务模型或板端性能。

## Requirements

### Requirement: 无保存的模拟可行性验证
检查 SHALL 在既有公司环境对 RV1126B 目标执行实际模型构建与 PC 软件模拟推理，结果只显示在终端。

#### Scenario: 软件模拟路径
- **WHEN** 小网络 ONNX 已加载并成功构建
- **THEN** 使用 target=None 初始化模拟器，对两组输入执行 inference 并比较参考输出

#### Scenario: 失败
- **WHEN** 转换、构建、模拟初始化或推理失败
- **THEN** 报告阶段与原因，不静默替换目标芯片或后端

#### Scenario: 清理
- **WHEN** 检查通过、失败或超时
- **THEN** 释放会话并清除专属 tmpfs 工作区及项目临时链接，不留下输入、输出、模型、报告或日志
