## Purpose

在公司既有环境中通过有界的真实反向传播与优化步骤验证代表模型能更新参数，仅在内存适配输入并保留原标注，明确未覆盖正式训练入口和持久化训练生命周期。

## ADDED Requirements

### Requirement: 有界无产物训练检查
检查 SHALL 在现有公司环境中用少量数据执行真实 loss、反向传播和 optimizer step；所有训练权重变化仅在内存生效。

#### Scenario: 动作训练输入
- **WHEN** Label Studio 帧区间准确对应本地视频
- **THEN** 仅在内存适配路径和标签，送入真实 MMAction2 数据预处理及 train_step，不修改原标注

#### Scenario: 梯度和更新验证
- **WHEN** 神经网络进行训练检查
- **THEN** loss 与梯度有限、至少一组梯度非零，且 optimizer step 后真实参数发生变化

#### Scenario: 无需训练
- **WHEN** 模块采用规则、变化点算法或推理后端
- **THEN** 跳过训练，不以额外前向代替训练检查

#### Scenario: 结果边界
- **WHEN** 汇报检查
- **THEN** 不保存数据、权重、日志或结果文件，明确合成监督、底层接口及正式训练入口未覆盖的限制
