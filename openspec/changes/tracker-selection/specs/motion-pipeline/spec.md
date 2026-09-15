## ADDED Requirements

### Requirement: 离线猫居中预处理管线（仅白天段）

跟踪环节 SHALL 由「抽样+插值」升级为经选型实验确定的真 MOT 跟踪器（多猫场景）。

#### Scenario: 跟踪器对比选型

- **WHEN** 固定同一检测源（GroundingDINO 白天检出），在 3–5 段人工核对过 track_id 的视频上分别运行候选跟踪器（ByteTrack/OC-SORT/BoT-SORT/DeepSORT）
- **THEN** 输出对比报告（IDF1/IDSW/轨迹碎片数/框平滑度），选型结论与判定标准一并记录，跟踪器接口为可插拔实现
