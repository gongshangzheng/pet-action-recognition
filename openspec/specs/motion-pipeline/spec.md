# motion-pipeline Specification

## Purpose
TBD - created by archiving change multi-object-detect-gate. Update Purpose after archive.
## Requirements
### Requirement: 空间关系状态层

系统 SHALL 基于检测框输出猫的空间关系状态：猫框底边中点落入家具框内 → `cat on {家具}`，否则 `on floor`；状态切换 MUST 满足持续 ≥1.5s 迟滞；判定 MUST 用底边中点而非框 IoU（防透视假象）。

#### Scenario: 猫跳上沙发

- **WHEN** 猫框底边中点持续 1.5s 以上落入沙发框内
- **THEN** 状态输出 `cat on sofa`，此前保持 `on floor`

#### Scenario: 猫路过桌子后方

- **WHEN** 猫框与桌框重叠但底边中点不在桌框内
- **THEN** 状态保持 `on floor`，不误判 `cat on table`

