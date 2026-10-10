# 标签分布只读审计规范

## Requirements

### Requirement: Read annotations without changing them
审计 SHALL 只读取现有 CSV/JSON，忽略取消标注和模型预测，不改原文件或规范化副本。
输入哈希 SHALL 在读取前后保持相同。脚本 SHALL 不加载视频或任何模型。

### Requirement: Report counts with explicit units
审计 SHALL 区分原始区间-标签对、去重区间、不同视频文件和合并后覆盖帧数。
同一类别在一个视频内重叠范围 SHALL 合并后计算覆盖，跨类别重叠 SHALL 独立报告。
秒数 SHALL 不基于未核实的统一 FPS 推算。

### Requirement: Preserve unknown and deferred labels
零观测 SHALL 只表示本次有效导出中没有该标签。
审计 SHALL 不删除稀少类别、不生成训练清单，也不将未知帧或暂缓类别当负例。
建议 SHALL 说明对本轮闭集范围的影响，不宣称覆盖全部项目要求。
