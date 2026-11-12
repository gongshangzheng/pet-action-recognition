# experiment-report-catalog Specification

## Purpose

规定实验报告的目录约定与主题级合并规则，使每个实验主题只有一篇可读的报告，读者不必按版本追读，也不会丢失「每一步做了什么、得到什么结果」的记录。

## Requirements

### Requirement: 一个主题一篇报告

报告目录 SHALL 按 `management/experiments/<topic>/<YYYYMMDD>-<主题短名>/` 组织，同一主题 MUST 只保留一篇现行报告。`<YYYYMMDD>` 取该主题最后一轮实验的日期，`<主题短名>` 说明对象与问题，不表示单次 run。

#### Scenario: 同一主题有新一轮实验

- **WHEN** 某主题完成了新一轮实验
- **THEN** 更新该主题的同一篇报告，把新一轮写进正文与运行谱系
- **AND** 不新增第二篇报告目录

#### Scenario: 报告被合并

- **WHEN** 多篇既有报告被合并为一篇
- **THEN** 被合并的目录删除，其案例、指标与结论进入合并后的报告
- **AND** 仓库内不再保留指向已删目录的链接

### Requirement: 合并报告交代各轮谱系

合并后的报告 SHALL 在附录中提供运行谱系，逐行列出该主题每一轮的日期、run id、做了什么、执行状态与产物路径。正文 MUST 按子问题组织，MUST NOT 按版本顺序堆叠过程记录。

#### Scenario: 多轮结论不可比

- **WHEN** 主题内两轮实验的样本量、配方或教师模型不同
- **THEN** 两者不放进同一张对比表作为结论
- **AND** 在正文或附录写明不可比的原因

#### Scenario: 数字溯源

- **WHEN** 读者要核对正文的任一数值
- **THEN** 该数值能在报告引用的产物或来源文档中找到原值
- **AND** 合并过程不重算、不补造数字

### Requirement: 历史记录吸收后保留可达路径

被合并进报告的历史文档 SHALL 保留原路径并转为指向报告的跳转，MUST NOT 直接删除已被其它文档引用的记录。归档 change（`openspec/changes/archive/`）MUST 保持原样，报告中以路径引用。

#### Scenario: 文档已被归档 change 引用

- **WHEN** 一份历史实验记录被吸收进报告，且归档 change 的 design 或 evidence 曾引用其路径
- **THEN** 原路径保留为跳转页，说明内容去向
- **AND** 归档文件不被修改

### Requirement: 合并后的完整度可判定

报告完整度 SHALL 由校验脚本按 `server/parsers/experiments_parser.report_problems` 的同一规则判定。任一报告缺 frontmatter 必填项、章节、evidence 六项、metric 字段或案例文件时，校验 MUST 失败并列出原因。

#### Scenario: 合并后校验

- **WHEN** 合并完成并运行校验脚本
- **THEN** 全部报告无 incomplete 原因，脚本零退出
- **AND** 失败时逐条打印缺失项，供作者补齐

### Requirement: 媒体只在正文展示

报告的图片与视频 SHALL 以 Markdown 内嵌形式出现在正文对应位置，MUST NOT 在页面末尾另设汇总区块。manifest 的 `cases` 是媒体登记与完整度判据，不是展示入口。

#### Scenario: 案例已登记但未嵌入

- **WHEN** 一份报告的 `cases` 里有条目没有出现在正文
- **THEN** 校验脚本把该报告判为 incomplete 并逐条列出未嵌入的案例
- **AND** 不由页面补渲染来掩盖缺失

#### Scenario: 正文引用了未登记的媒体

- **WHEN** 正文嵌入的 `assets/` 或 `media/` 文件没有在 `cases` 登记
- **THEN** 校验脚本报错，且 media 路由拒绝服务该文件
