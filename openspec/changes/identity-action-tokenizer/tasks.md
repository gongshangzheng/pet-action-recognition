# Tasks: identity-action-tokenizer

> 总管：`pet-motion-latent-pipeline`。**研究型**：两阶段（A 人类 UCF101 → B 猫语料）。严格按编号顺序；GPU 任务前 nvidia-smi 查占用。
> 前置：`pet_vjepa` 环境（transformers ≥4.55，待建）。

- [ ] 1.1 配方精读：TiTok（2406.07550）/ AdapTok（2505.17011）/ 1d-tokenizer / FLOAT 训练细节（mask 策略/解码器规模/LR/epoch），沉淀训练配方笔记
- [ ] 1.2 `pet_vjepa` 环境：clone plf + transformers ≥4.55 + 验证 V-JEPA 2 fpc16 加载与特征提取（不动 plf）
- [ ] 1.3 UCF101 manifest：NAS UCF-101 → 窗口清单（16 帧/窗）+ 缓存 patch tokens（冻结骨干，一次性 ~半天）
- [ ] 1.4 tokenizer 实现：瓶颈交叉注意力身份 tokens（K_id=32）+ 逐帧动作 query（z_t 32d）+ 轻量解码器；`configs/identity_tokenizer/`
- [ ] 1.5 阶段 A 训练（UCF101，重建 + 动作 CE + 类别弱监督）：LPIPS/PSNR 曲线 + token 数缩放实验（8/16/32 tokens）
- [ ] 1.6 阶段 A 验收：z_t 线性探针 top1（101 类）+ 身份 dropout/交换消融 → 架构可行性判定（**中期检查点**）
- [ ] 1.7 阶段 B 猫语料迁移：mammal_v0 + cats v1 + followcam 继续训练，e_id 接入 track 级 InfoNCE + 跨猫交换重建
- [ ] 1.8 阶段 B 评测矩阵（design T-A4 全表）：重建/动作探针（5 类）/身份检索/身份泄漏/交换重建 → 总报告
- [ ] 1.9 结论裁定（**用户验收**）：CatHuBERT 骨干是否采用本 tokenizer；产出回流 video-feature-latent 任务 1.7
