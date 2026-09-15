# Design: spot-check-cli

> 继承总管 D4（抽查式 CLI 定位）、D7（身份三层答案）、D9（登记-检索架构）。

## Decisions

### C1: CLI 形态

`scripts/spot_check_actions.py --camera C --from T --to T`：拉录像 → 复用预处理管线（multi prompt 检测 + 运动校正 + 跟随裁剪）→ 隐码（video-feature-latent 选型胜出编码器 + 簇映射）→ 动作报告（JSON/Markdown）。分钟级延迟可接受。

### C2: 身份登记

登记照（每猫 3–5 张清晰 crop）→ DINOv2 embedding → FAISS；新 crop 最近邻检索；未登记个体标「未知猫 #N」。与物品识别共用 `petlib/identity/` 抽象（总管 D9）。
