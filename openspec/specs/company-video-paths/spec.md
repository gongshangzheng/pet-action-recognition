# company-video-paths Specification

## Purpose

将 Label Studio 视频引用精确映射到可读的本地路径，只生成地址修正副本并保护视频与原标注，保留全部动作区间及取消状态，为后续独立训练准备提供可核查的路径来源。

## Requirements

### Requirement: 完整且精确的视频地址映射
转换器 SHALL 将支持的 Label Studio 视频引用转换为实际可读的本地绝对路径，
仅接受精确且唯一的文件对应，不依赖 Label Studio 服务运行。

#### Scenario: 上传引用
- **WHEN** 输入为 `/data/upload/.../<上传前缀>-<文件名>`
- **THEN** 优先精确匹配原文件名，仅在必要且可精确匹配时去除单个八位十六进制前缀

#### Scenario: local-files 引用
- **WHEN** 输入为 `/data/local-files/?d=<目录/文件名>`
- **THEN** 从唯一的 `d` 参数解析文件名并精确匹配，不只读取 URL path

#### Scenario: 已规范化路径
- **WHEN** 输入已为视频根目录内的真实绝对路径
- **THEN** 保留该地址，验证可读性，不重复剥离前缀

#### Scenario: 缺失或歧义
- **WHEN** 引用格式不支持、文件缺失、不可读、越出视频根目录或存在歧义
- **THEN** 明确报告失败，不通过模糊匹配生成最终标注副本

### Requirement: 标注内容与原文件保护
转换器 SHALL 只在新副本中改变 CSV 的 `video` 和 JSON 的 `data.video` 值，
保留其他全部字段值、记录顺序及原文件。

#### Scenario: 行为标注
- **WHEN** CSV 行包含 `behavior` 或 JSON task 包含动作、区间、取消状态及其他字段
- **THEN** 所有非地址值保持相同，不重写标签、区间，不筛除记录，不转换训练标签

#### Scenario: 来源保护
- **WHEN** 转换完成并回读核验
- **THEN** 原 CSV/JSON SHA256 不变，视频不被改名、移动、复制或重编码

### Requirement: 可核验的项目内产物
转换器 SHALL 将映射版 CSV/JSON 保存在项目数据目录，另存映射审计，
不向标注增加审计字段，不将文件准备冒充模型训练验收。

#### Scenario: 验收报告
- **WHEN** 汇报转换结果
- **THEN** 给出实际计数、完整路径对应检查、非地址字段比较、原标注哈希及产物位置

#### Scenario: 执行范围
- **WHEN** 执行本 change
- **THEN** 只修复地址并核验文件，不安装依赖，不启动训练、前向或模型评估
