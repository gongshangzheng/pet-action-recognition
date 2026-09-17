# Tasks: identity-action-tokenizer

> 总管：`pet-motion-latent-pipeline`（**2.3 主线**，encoder 优先）。两阶段：A 人类 UCF101 → B 猫语料。
> 架构 = **TivTok SIF 双 token + FLOAT/LIA 正交运动基（连续潜空间，无量化）**（详见 design.md）。严格按编号顺序；GPU 任务前 `nvidia-smi` 查占用。
> 前置：`pet_tokenizer` 环境（待建）；`pet-background-removal` 抠像语料（阶段 B 需要）。

## 1. 准备

- [ ] 1.1 配方精读：TivTok SIF（2606.17590）/ LIA 正交基（2203.09043，代码用 QR）/ FLOAT 分解（2412.01064）/ DeRA 对齐（2512.04483）/ **无量化先例（TiTok VAE 模式 / MAR 2406.11838）**，沉淀训练配方笔记
- [ ] 1.2 `pet_tokenizer` 环境：独立 conda（不污染 plf），安装依赖 + 验证 GPU 可用
- [ ] 1.3 UCF101 manifest：NAS UCF-101 → 16 帧窗口清单（stride 8），核对总量与可用性

## 2. Tokenizer 实现

- [ ] 2.1 **FLOAT 式身份-运动分解骨架**：视频编码器（全片段提特征，保证运动有时序上下文）→ 逐帧 latent → 正交基投影得 `λ_t`；参考输入编码得 `w_identity`（**TivTok SIF 双 token 暂不采用**，见 design 谱系 + `papers/docs/tivtok-reference.md`）
- [ ] 2.2 动作通道：FLOAT/LIA 正交运动基（可学习矩阵 + 每次前向 `torch.linalg.qr`）→ z_t = Σ λ_m(t)·v_m；系数 λ 可闭式提取（λ_m = <z_t, v_m>）
- [ ] 2.3 解码器 + 重建损失（L1 + perceptual + adversarial，TivTok 口径）
- [ ] 2.4 **身份通道：参考输入 + FLOAT 式读出（T-A5）** —— 身份编码器（卷积编码器 → 512 维全局向量）**只吃参考**；单图直接用，多图/视频逐图编码后**平均**；与运动分支**独立前向**；身份监督由重建承担（无需独立身份损失）
- [ ] 2.4b 参考输入数据准备：为每只猫收集参考（单图/多图/短视频）；单猫语料只需一份；建“片段→参考”配属表
- [ ] 2.5 跨猫交换重建（解耦验证）：**换参考输入即得**（`decode(参考_B, A 的 λ)`）——无需专门训练目标
- [ ] 2.6 `configs/identity_action_tokenizer/` 配置 + 训练脚本（bf16 + 梯度检查点）

## 3. 阶段 A（UCF101，人类数据）

- [ ] 3.1 阶段 A 训练：UCF101，重建 + 动作伪行为素 CE；监控 LPIPS/PSNR
- [ ] 3.2 超参搜索：N_TIV（8/16/32）、N_TV、M（正交基元数，16/32/64）
- [ ] 3.3 阶段 A 验收（**中期检查点**）：z_t 线性探针 top1（101 类）+ λ_m 基元曲线可视化 + v_m 可视化 → 架构可行性判定

## 4. 阶段 B（猫语料迁移）与验收

- [ ] 4.1 抠像猫语料迁移训练（依赖 `pet-background-removal` 产物）：mammal_v0 + cats_v1 + followcam
- [ ] 4.2 阶段 B 评测矩阵（design T-A8 全表）：重建 / 动作探针（5 类）/ λ 可解释性 / 身份检索 / 视角无关性（≥0.7）/ 身份泄漏 / 跨猫交换重建
- [ ] 4.3 总报告 + 结论裁定（**用户验收**）：编码器是否供 `video-feature-latent` 消费
