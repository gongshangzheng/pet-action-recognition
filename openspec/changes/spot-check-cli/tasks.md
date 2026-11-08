# Tasks: spot-check-cli

> 总管：`pet-system-integration`。**前置：无**（`video-feature-latent` 已搁置，隐码与行为簇不再作为前置；段列表改由 `video-action-segmentation` 提供）。严格按编号顺序执行。
> ⚠️ 下列任务文本中的「隐码」与「簇分配」属于旧方案，当前方案待按新前置重写，执行前先核对 `video-action-segmentation` 的段列表契约。

- [ ] 1.1 `scripts/spot_check_actions.py`：摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/MD：标签/起止秒/track_id/登记身份/置信度/疑似新动作/猫在场率/空间状态段）
- [ ] 1.2 `scripts/register_cats.py`：猫个体档案（登记照 → embedding（模型待实测）→ 向量库检索），未登记个体标「未知猫 #N」；与物品识别共用登记-检索抽象（总管 D9）；模型选型见 `registry-retrieval` design D9b
- [ ] 1.3 端到端联调：3 个真实时段（含 1 个无猫时段）出报告
- [ ] 1.4 L2 边界误差抽查：动作码突变 = 切换边界，误差须在滑窗粒度 ±1.5s 内
