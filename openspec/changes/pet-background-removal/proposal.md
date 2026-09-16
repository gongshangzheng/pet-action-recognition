## Why

followcam 视频中相机随猫移动，**背景持续变化**——这破坏了下游 tokenizer 的核心假设。TivTok 式双 token 架构假设"背景稳定"（TIV 抓稳定的身份信息，TV 抓逐帧残差），但我们的场景里背景本身就在动，若不处理，**TV（动作）tokens 会把相机运动与场景变化当作"动作"学进去**，污染动作表征、毁掉行为发现的语义。

解决方案：在预处理阶段把**猫本体抠出**（其余置黑），让下游只学猫本体。空间上下文（在床上/沙发上/地上）已由 `multi-object-detect-gate` 的空间关系状态层独立处理，抠像不丢信息。

## What Changes

- 新增**猫本体抠像（背景移除）预处理管线**：输入视频 → 输出"猫本体 + 黑背景"视频（沿用项目已有黑边约定）
- **方案选型**（又快又好，实测后定）：SAM2（视频分割，时序一致，复用现有 GroundingDINO 检测框作 prompt）/ RVM（Robust Video Matting，毛发边缘更细）/ 其他
- **全语料批处理**：followcam 34 段 + mammal_v0 2234 + cats v1 717
- **质量门槛与兜底**：掩码面积异常、时序漂移、检测丢失帧的检出与回退
- CLI + 产物约定（黑背景 mp4，与原视频并存，不覆盖）

## Capabilities

### New Capabilities
<!-- 无新 capability：本条属于运动管线预处理，沿用既有 motion-pipeline -->

### Modified Capabilities

- `motion-pipeline`: 新增"猫本体抠像（背景移除）"要求——给定视频与猫检测框，系统 SHALL 输出仅含猫本体、背景置黑的视频，且 MUST 具备掩码质量兜底

## Impact

- 新增 `scripts/` 抠像 CLI + 模型依赖（SAM2 或 RVM 权重，pet 执行）
- 新增产物目录（抠像视频，独立于原视频）
- **消费方**：`identity-action-tokenizer`（阶段 B 猫语料训练）、`video-feature-latent`（可选对比）
- 与原视频、followcam 产物并存，不破坏既有管线
- GPU 任务在 pet 执行（4090）
