## Purpose

定义前沿模型接入训练 registry 的规范：本地 config 与 registry 条目的接入方式、姿态桥接流水线的行为契约、远端验证要求，保证新模型接入不修改 vendor、可重复、可在训练模块前端直接选用。

## ADDED Requirements

### Requirement: Registry 条目接入规范

训练 registry（`server/routers/training.py::_MMACTION2_REGISTRY`）新增条目 SHALL 包含完整字段（id/name/family/backbone/pretrained_source/pretrained_url/mmaction2_config/description），且 mmaction2_config 指向本地 config 或 vendor config 相对路径；本地 config MUST 通过 `_base_` 继承或完整定义，禁止修改 `models/mmaction2/` 只读目录。

#### Scenario: VideoMAE v1 接入后可选

- **WHEN** 训练模块加载 registry
- **THEN** 存在 videomae-v1 条目，字段完整，config 路径有效，pretrained_url 可下载

#### Scenario: UniFormerV2 接入后可选

- **WHEN** 训练模块加载 registry
- **THEN** 存在 uniformerv2 条目，字段完整，config 路径有效

### Requirement: 姿态桥接流水线

系统 SHALL 提供从宠物视频到骨架动作识别的转换流水线：关键点提取脚本（SuperAnimal-Quadruped 零样本）输出逐视频关键点序列；转换脚本将关键点映射为 PoseC3D 兼容格式（AP-10K 四足 17 点口径）；骨架 config（PoseC3D/STGCN++）可在训练模块中触发。

#### Scenario: 视频转关键点

- **WHEN** 对含宠物的视频段执行关键点提取脚本
- **THEN** 输出逐帧关键点坐标与置信度（JSON/NPZ），低置信度帧有标记，脚本可批量执行且幂等（同输入同输出路径不重复计算）

#### Scenario: 关键点转 PoseC3D 格式

- **WHEN** 对提取的关键点执行转换脚本
- **THEN** 产出 PoseC3D 兼容的 npz 输入（keypoint + keypoint_score 两数组），点数/维度符合骨架 config 声明，无法映射的关键点按 AP-10K 口径丢弃并在日志说明

#### Scenario: 骨架模型可训练

- **WHEN** 在远端以转换产物为数据集触发骨架训练
- **THEN** PoseC3D 或 STGCN++ config 能完成至少 1 个 epoch 的冒烟训练

### Requirement: AIM Adapter 微调接入

AIM（Adapting Image Models）的 Adapter 模块 SHALL 以独立模块文件 + config `custom_imports` 方式接入（vendor 目录零修改）：backbone 冻结、仅训练 Adapter/头部的参数分组在 config 中显式声明；接入后可作为 registry 模型触发训练。

#### Scenario: AIM config 只训 Adapter

- **WHEN** 检查 AIM 训练 config 的 optim/paramwise 配置
- **THEN** backbone 参数被冻结（requires_grad=False），可训练参数仅 Adapter、头部与 norm 层

#### Scenario: AIM 冒烟训练

- **WHEN** 在远端以 cats 数据集触发 AIM 训练（最小轮数）
- **THEN** 训练完成且显存占用低于全量微调同规模 run 的参照值

### Requirement: 接入文档

系统 SHALL 在文档中维护接入路线图：每个接入项的 config 位置、权重下载方式、远端触发命令、已知坑（如 VideoMAEv2 的 --pretrained 冲突），与 `papers/docs/research-landscape.md` 路线图互链。

#### Scenario: 文档可指导复现

- **WHEN** 新成员按文档操作
- **THEN** 能在远端复现任一接入项的冒烟训练，无需口头交接
