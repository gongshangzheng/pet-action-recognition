## Why

摄像头厂商材料包含设备接入链路、联调顺序和验收边界，但这些信息尚无项目 skill 入口，容易与本仓 Live 功能或行为指标上报混淆。

## What Changes

- 新增项目 skill，指导厂商对接任务读取材料、区分链路并记录验收证据。
- 区分 V0.2 联调基线、双方待确认事项和未经验证的实际能力。
- 不修改 AGENTS.md，不实施设备联调、协议或产品功能。

## Capabilities

### New Capabilities

无。本 change 整理指导材料，不新增产品行为，因此跳过规格变更。

### Modified Capabilities

无。

## Impact

拟新增 `.agents/skills/camera-vendor-integration/SKILL.md`。参考厂商 V0.2 材料和现有 `live` skill；不修改服务、设备、接口或原始材料。厂商材料当前未跟踪，是否入库及其分发权限不在本 change 中决定。
