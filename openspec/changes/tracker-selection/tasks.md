# Tasks: tracker-selection

> 总管：`pet-motion-latent-pipeline` §4A。**延后**：多猫数据出现时启动；启动前请先核对 BoxMOT Re-ID 权重是否已就位（BotSort/DeepOcSort 契约测试当前跳过）。

- [ ] 1.1 GT 制作：抽 3–5 段白天视频（含多猫），人工核对 track_id
- [ ] 1.2 固定检测源缓存 + 运行四候选
- [ ] 1.3 指标计算：IDF1（主）/IDSW/轨迹碎片数/框平滑度
- [ ] 1.4 选型报告 + 结论（决定 spot-check-cli 默认跟踪器）→ archive

> 备查记录：检测器侧误报抑制阈值扫描已预跑——0.3→0.5 均无法抑制沙发超宽框（高置信检出）；沙发漂移由渲染层尺寸离群过滤兜底，multi-object-detect-gate 验收后升级为沙发框语义校验。
