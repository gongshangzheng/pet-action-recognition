# 标签分布只读审计规范

## Purpose

本能力以只读方式审计原始动作区间与标签分布，保留未知、取消和暂缓类别的语义，明确统计单位及结论边界，为后续独立的数据方案提供可追溯依据。

## ADDED Requirements

### Requirement: Read annotations without changing them
审计 SHALL 只读取现有 CSV/JSON，忽略取消标注和模型预测，不改原文件或规范化副本。
输入哈希 SHALL 在读取前后保持相同。脚本 SHALL 不加载视频或任何模型。

#### Scenario: 输入保持原样
- WHEN 审计完成
- THEN 输入哈希与审计前一致，且没有加载视频或模型

### Requirement: Report counts with explicit units
审计 SHALL 区分原始区间-标签对、去重区间、不同视频文件和合并后覆盖帧数。
同一类别在一个视频内重叠范围 SHALL 合并后计算覆盖，跨类别重叠 SHALL 独立报告。
秒数 SHALL 不基于未核实的统一 FPS 推算。

#### Scenario: 统计口径可复核
- WHEN 同类区间在同一视频重叠
- THEN 合并同类覆盖帧数并单独报告跨类重叠，不用未核实 FPS 推算秒数

### Requirement: Preserve unknown and deferred labels
零观测 SHALL 只表示本次有效导出中没有该标签。
审计 SHALL 不删除稀少类别、不生成训练清单，也不将未知帧或暂缓类别当负例。
建议 SHALL 说明对本轮闭集范围的影响，不宣称覆盖全部项目要求。

#### Scenario: 零观测不代表负例
- WHEN 某类在有效导出中没有观测
- THEN 报告零观测及闭集范围限制，不删除类别或生成训练清单
