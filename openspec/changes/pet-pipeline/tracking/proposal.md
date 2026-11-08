# Proposal: tracker-selection

## Why

训练数据准备与在线 YOLO 推理都可能把同一只猫或狗的重复检测框当作多个目标。仅凭同帧重叠也可能误删靠近或交叉的两只真实动物；需要结合位置随时间的连续性，与目标关联共同处理，并保留不确定性。已有单流 OC-SORT 是运行过的基线，不代表多宠身份质量已验收或已完成最终选型。

## What Changes

- 保存 raw 后先处理明显同帧重复，再结合过去观测及既有轨迹复核，按证据和获批规则处理；关联与重复判断相互反馈。位置连续性是线索而非身份保证，不默认取框的包围 union。
- 训练数据准备及在线 YOLO 共用因果部分，仅使用当前和过去信息；离线可另行采用未来帧复核并明确标记。规则、候选、人工 GT 与预算先由用户按实际案例裁定。
- 固定已有检测输入和人工口径，分别评估离线及在线结果，比较获选候选并由用户决定接入范围；不自动回退、设置默认或归档。
- 对接 `pet-pipeline` 既有逐帧框与裁剪能力，不重复数据导出。raw 教师检测独立于本队列。

候选建议和局限见 [research](research.md)，14 项串行任务见 [tasks](tasks.md)，旧九项原文与映射见 [task-map](task-map.md)。当前规划为未来合同，不代表实现或评测完成。

## Capabilities

### Modified Capabilities

- `motion-pipeline`：修订现有白天猫离线管线的跟踪合同，保留无关能力；另补猫狗训练数据准备与在线推理共享的重复框处理合同。

## Impact

预计影响 `petlib/tracking/`、跟踪调用入口和已有裁剪能力的对接。GroundingDINO 教师原始检测、学生训练及数据集构建仍由 [`pet-pipeline`](../pet-pipeline/design.md) 管理；系统统筹见 [`pet-system-integration`](../pet-system-integration/design.md)。现有跟踪规格的归属和一致性仍待协调，详见 design；本 delta 尚未同步主 spec。

本 change 不要求全算法 benchmark、全量人工标注、新训练或付费，也不授权检测、权重下载或远程运行。旧 proposal 全文按提交 `5900669674ef318d8adc88b5ba5fa0a0eae5dabb` 原样保存在 [history-proposal](history-proposal.md)，仅为历史而非执行权威。
