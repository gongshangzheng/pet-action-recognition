# Tasks: registry-retrieval

> 总管：`pet-motion-latent-pipeline` §4B。**延后**：实施需用户批准；建议与 `spot-check-cli` 猫 Re-ID 联调时启动。

- [ ] 1.1 （待批准）统一登记-检索库：登记照 → DINOv2 embedding → FAISS；猫与物品共用一套
- [ ] 1.2 （待批准）静态物体候选生成：SAM 一次性分割（固定机位缓存 + 定期重分割）+ 帧差变更触发
- [ ] 1.3 （待批准）物品实例识别闭环：SAM mask 候选 → DINOv2 检索判定；OWLv2 图像引导作对照；GDINO LoRA 室内微调仅作最后手段备档
- [ ] 1.4 （待批准）猫 Re-ID 联调：与 spot-check-cli 的 register_cats.py 合并设计
