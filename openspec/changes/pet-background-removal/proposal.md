## Why

followcam 视频中相机随猫移动，**背景持续变化**——这破坏了下游 tokenizer 的核心假设。TivTok 式双 token 架构假设"背景稳定"（TIV 抓稳定的身份信息，TV 抓逐帧残差），但我们的场景里背景本身就在动，若不处理，**TV（动作）tokens 会把相机运动与场景变化当作"动作"学进去**，污染动作表征、毁掉行为发现的语义。

解决方案：在预处理阶段把**猫本体抠出**（其余填充**白色**固定背景），让下游只学猫本体。空间上下文（在床上/沙发上/地上）已由 `multi-object-detect-gate` 的空间关系状态层独立处理，抠像不丢信息。

## What Changes

- 新增**猫本体抠像（背景移除）预处理管线**：输入视频 → 输出"猫本体 + **白背景**"视频（纯色常量填充；**非** speedrun 的黑 margin 约定，那是标注视频的 letterbox）
- **方案选型（2026-09-17 修订）**：以 **实时小模型** 为主——`rembg`（MIT）承载的轻量背景移除模型（候选 `u2net` / `u2netp` / `silueta` / `isnet-general-use` / `birefnet-general-lite`），按**许可 + 掩码质量 + 时序稳定性 + 速度**四项实测后定
- **移除方案**：**SAM 不再承担猫本体抠像**（用户裁定 2026-09-17）——SAM 改用于背景对象层（维护背景物件清单 + 纠正/补全 GroundingDINO，仅关键帧触发），属独立 change；RVM（GPL-3.0 传染）与 RMBG 系（非商用许可）否决
- **全语料批处理**：followcam 34 段 + mammal_v0 2234 + cats v1 717
- **质量门槛与兜底**：掩码面积异常、时序漂移（帧间闪烁）、**掩码与检测框不一致**、检测丢失帧的检出与回退
- CLI + 产物约定（白背景 mp4，与原视频并存，不覆盖）

## Capabilities

### New Capabilities
<!-- 无新 capability：本条属于运动管线预处理，沿用既有 motion-pipeline -->

### Modified Capabilities

- `motion-pipeline`: 新增"猫本体抠像（背景移除）"要求——给定视频与猫检测框，系统 SHALL 输出仅含猫本体、背景填充固定纯色（默认白）的视频，且 MUST 具备掩码质量兜底

## Impact

- 新增 `scripts/` 抠像 CLI + 模型依赖（**`rembg` + ONNX Runtime + 小模型权重**，pet 执行）
- 新增产物目录（抠像视频，独立于原视频）
- **为 L8 实时监控模式预留**：选型为**实时可用级小模型**（GPU 几十毫秒/帧）；本 change 仍只交付离线批处理，不做在线服务
- **消费方**：`identity-action-tokenizer`（阶段 B 猫语料训练）、`video-feature-latent`（可选对比）
- 与原视频、followcam 产物并存，不破坏既有管线
- GPU 任务在 pet 执行（4090）
