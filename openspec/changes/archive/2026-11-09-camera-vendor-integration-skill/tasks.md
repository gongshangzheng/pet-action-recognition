## 1. 整理与核验

默认按编号严格串行，前一项的完成判据满足后才开始下一项。

- [x] 1.1 编写 `.agents/skills/camera-vendor-integration/SKILL.md`。完成判据：文件覆盖接入范围、联调顺序、证据边界和材料入口，区分文档基线、待确认事项与未执行验收。
- [x] 1.2 检查新 skill 与 `.agents/skills/live/SKILL.md` 的触发范围。完成判据：检查结果记录在本 change 的 `evidence.md`，且能区分厂商设备对接与本仓 Live 功能。
- [x] 1.3 核验新 skill 的材料引用和安全边界。完成判据：在 `evidence.md` 记录路径及章节检查结果，确认不含真实凭据、含 OpenSpec 审批提示，且未把联调草案表述为已验收事实。
