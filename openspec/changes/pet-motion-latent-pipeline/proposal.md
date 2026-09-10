# Proposal: pet-motion-latent-pipeline

## Why

宠物动作识别（PAR）需要一条「从原始监控视频到动作语义」的完整管线。当前缺失三个环节：① 输入预处理——猫没有被定位/居中/跟踪，整帧输入存在背景捷径与分辨率浪费；② 动作表征——没有宠物动作隐空间，类别表靠人工拍脑袋（cats 数据 activity 伞类占标注一半）；③ 推理形态——生产场景不需要 7×24 实时监测，而是**非实时抽查**（猫可能不在画面内、抽查而非全时），现有 live 实时管线不匹配该形态。数字人社区的 motion latent 范式（VASA-1/Ditto/Avatar Forcing/FLOAT，见综述 §4.4）提供了成熟架构，动物行为学（Keypoint-MoSeq）提供了目标函数。

## What Changes

- **离线数据预处理管线**（训练数据生产）：
  - GroundingDINO（开放词汇检测）→ 跟踪器（ByteTrack/OC-SORT/BoT-SORT 候选，实验对比选型）→ 关键点提取（SuperAnimal vs ViTPose+ 双候选对比），对白天段视频批处理；HQSAM 作为可选 mask 消融阶段
  - 产出三类资产：① 每猫轨迹的**猫居中跟随视角视频**（cat-fixed stabilized video）；② 逐帧关键点序列（SuperAnimal，含置信度）；③ 伪标注框（供 YOLO11 微调）
  - 范围收敛（用户确认）：**仅处理白天段**（79 段中 34 段），夜间红外段暂不处理（二期再议）
- **运动隐空间提取器训练**（核心新模型）：
  - 输入：关键点序列（48×34），**自监督重建**，无动作标签
  - 架构：identity-motion 双分解（E_mot 逐帧动作码 32 维 + E_id 静态身份码 64 维）+ VQ 码本（K=512 动作 token）+ 解码器；损失 = 重建 + 速度匹配 + VQ + 身份对比 + 平滑正则
  - 训练数据：cats 717 clips + pet_action_mammal_v0 2234 段 + live 无标注录像（按源视频分组切分，防泄漏）
- **抽查式推理管线**（生产形态，非实时）：
  - 用户指定「某摄像头某时间段」→ 管线自动：检测→居中裁剪→持续跟踪→关键点→隐码→输出动作报告（L1 标签 + L2 时间段 + L3 新动作簇提示）
  - 明确**不做逐帧实时**：动作结果按秒级粒度输出；GroundingDINO 系仅在此离线/抽查路径使用
- **评测协议**：线性探针 top1（目标 ≥ 端到端微调 80%）、L3 聚类 vs 人工标签 NMI、隐码可遍历性

## Capabilities

### New Capabilities

- `motion-pipeline`: 猫居中预处理（检测→跟踪→稳定裁剪）与运动隐空间提取器的行为契约——含离线批处理、抽查式推理、隐空间训练与评测要求

### Modified Capabilities

（无）

## Impact

- **新增脚本**：`scripts/` 下 GroundingDINO/HQSAM/ViTPose 批处理、轨迹平滑、猫居中裁剪、隐空间训练/评测（约 6–8 个）
- **新增模型代码**：motion latent 模块（编码器/码本/解码器/损失）
- **数据资产**（gitignore）：`datasets/cats/followcam/`（跟随视频）、`keypoints/`（NPZ）、隐空间 checkpoint
- **依赖**：GroundingDINO、HQSAM、ViTPose 需在 pet 安装（deeplabcut 之外的另一套环境，需隔离）
- **明确不做**：live 实时路径改动（已在线）；7×24 连续监测

## 假设记录

- 生产推理形态 = **非实时抽查**（用户确认）：按需分析指定时间段，秒级粒度输出，可接受分钟级处理延迟
- 范围 = 白天段（34/79）；夜间红外 45 段存在检测/关键点域差，**二期**再议（届时需 YOLO11 夜视微调 + IR 关键点质量验证）
- SuperAnimal 关键点在白天段的质量同样需抽查验证（关卡前移，但风险低）
- 训练数据量级：cats 4 万+ 窗口、mammal_v0 扩 4 倍——VQ 码本 K=512 起步
