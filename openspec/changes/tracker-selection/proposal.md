# Proposal: tracker-selection

> 子 change，总管：`pet-motion-latent-pipeline`。**状态：延后**——单猫白天场景「抽样检测+插值」已验收足够；多猫数据出现时启动。

## Why

单猫场景无需真 MOT（总管 D1 裁定）；多猫同框时插值方案失效，必须从 BoxMOT 四候选（ByteTrack/OC-SORT/BoT-SORT/DeepSORT）中实验选型。GatedTracker 方案已否决（总管 D1b：门控治标不治本，且沙发误检已由渲染层过滤兜底）。

## What Changes

- 小样本 GT 制作（3–5 段含多猫，人工核对 track_id）
- 固定同一 GroundingDINO 检测源，四候选同台对比
- 指标：IDF1（主）/ IDSW / 轨迹碎片数 / 框平滑度 → 选型报告（决定 spot-check-cli 默认跟踪器）

## Capabilities

### Modified Capabilities

- `motion-pipeline`: 跟踪器由「抽样+插值」升级为真 MOT（选型结论驱动）

## Impact

- petlib tracking 四实现已就位（契约测试 13 过）；本 change 只做选型实验，零新代码预期
- 前置条件：多猫视频数据出现
