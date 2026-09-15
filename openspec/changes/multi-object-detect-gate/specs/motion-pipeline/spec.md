## MODIFIED Requirements

### Requirement: 离线猫居中预处理管线（仅白天段）

系统 SHALL 提供离线批处理管线（GroundingDINO 检测 + 跟踪 + HQSAM/ViTPose 可选），处理范围为**白天段**（夜间红外段二期处理），将输入视频转换为：① 每猫轨迹的猫居中稳定裁剪视频；② 逐帧关键点序列（含置信度，**辅助信号**）；③ 伪标注框包。跟踪 MUST 提供身份连续（track_id）、漏检帧插值补全、轨迹平滑三项能力。**检测环节 SHALL 支持多 prompt 一次前向**（默认 `cat. bed. table. sofa. shelf.`），家具框与猫框一并落盘。

#### Scenario: 单猫视频生成跟随视角

- **WHEN** 对一段单猫视频执行批处理
- **THEN** 输出恰好一条猫居中稳定视频，画面中猫保持居中，帧间无跳切抖动

#### Scenario: 多猫视频逐猫输出

- **WHEN** 输入视频同框出现两只猫
- **THEN** 输出两条独立轨迹的跟随视频，且整段视频内 track_id 不互换

#### Scenario: 多目标同帧检测

- **WHEN** 以多 prompt（cat + 家具类）执行一次前向
- **THEN** 返回各类物体的框与置信度；猫检出率不低于单 prompt 基线（98%），家具框位置经人工抽检正确

#### Scenario: 漏检帧补全

- **WHEN** 检测器在某帧未检出猫
- **THEN** 跟踪器以运动预测插值该帧框位置，轨迹不中断，且该帧被标记为「低置信插值」

## ADDED Requirements

### Requirement: 空间关系状态层

系统 SHALL 基于检测框输出猫的空间关系状态：猫框底边中点落入家具框内 → `cat on {家具}`，否则 `on floor`；状态切换 MUST 满足持续 ≥1.5s 迟滞；判定 MUST 用底边中点而非框 IoU（防透视假象）。

#### Scenario: 猫跳上沙发

- **WHEN** 猫框底边中点持续 1.5s 以上落入沙发框内
- **THEN** 状态输出 `cat on sofa`，此前保持 `on floor`

#### Scenario: 猫路过桌子后方

- **WHEN** 猫框与桌框重叠但底边中点不在桌框内
- **THEN** 状态保持 `on floor`，不误判 `cat on table`
