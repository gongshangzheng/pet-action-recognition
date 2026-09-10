## Purpose

检测链（t13-1 YOLO11）第一阶段准备能力：对现有 cats 视频跑 COCO 预训练 zero-shot 体检产出选型证据，导出 LabelStudio 可导入的预标注包，并固定标注类目定义（含中期验收特征映射），为 9 月人工标注与微调铺路。

## ADDED Requirements

### Requirement: Zero-shot 批量体检报告

系统 SHALL 提供 CLI 脚本，对指定目录下全部 cats 视频运行 COCO 预训练 YOLO11 推理（支持 n/s 两档模型），并产出结构化体检报告（Markdown + JSON）：逐视频与汇总的 cat/person/bowl 三类检出帧率、平均置信度、帧数。

#### Scenario: 全量视频统计
- **WHEN** 对 79 段 cats 视频运行体检脚本
- **THEN** 报告包含每段视频的 per-class 检出帧率与均值 conf，以及全量汇总

#### Scenario: 白天/夜视双口径分组
- **WHEN** 报告生成
- **THEN** 统计按「拍摄小时」与「帧成像特征」两种口径分别给出白天/夜视分组数字；成像特征口径 SHALL 将亮度低于阈值**或彩色饱和度低于阈值**的帧计为夜视帧（红外夜视帧被补光灯打亮、亮度不低但几乎无色），夜视组的 cat 漏检率可单独读出

#### Scenario: 单视频失败不中断整批
- **WHEN** 某段视频解码失败或零帧可读
- **THEN** 脚本跳过该视频、在报告的失败清单中记录原因，其余视频正常完成

### Requirement: 抽样标注视频

体检运行 SHALL 按白天/夜视分层抽样导出画框视频（框上标注 COCO 类名与置信度），供人工评判框质量。

#### Scenario: 抽样覆盖昼夜两组
- **WHEN** 体检完成
- **THEN** 导出的标注视频中白天组与夜视组各至少有其抽样段的代表（默认各 4 段，数量可由 CLI 参数调整）

### Requirement: 预标注帧导出

体检运行 SHALL 导出预标注帧包：按可配置帧率（默认每 2 秒 1 帧）抽帧，输出图像文件 + YOLO 格式标注 txt + 类目映射文件，并打包为 LabelStudio 可导入的任务包（含 predictions）。

#### Scenario: 帧率可控
- **WHEN** 以 `--frame-interval 2` 运行
- **THEN** 每段视频导出帧的平均间隔约为 2 秒，且 CLI 参数反映在产物 README 中

#### Scenario: COCO 类映射到定稿类目
- **WHEN** 导出预标注
- **THEN** COCO `cat`/`person` 分别映射为定稿类目的对应类；COCO 无法区分的 `bowl` 映射为中间类 `bowl_unspecified`（待人工细分为食盆/水盆），映射关系写入类目映射文件

#### Scenario: 无检出帧仍导出图像
- **WHEN** 某帧无任何 COCO 检出
- **THEN** 该帧图像仍进入任务包（标注为空），供人工补标

### Requirement: 标注类目定稿文档

仓库 SHALL 包含标注类目定稿文档：t13-1 原类目（猫、人、食盆、水盆、猫砂盆、玩具、门窗）之外增加 `cat_face` 类；每类给出边界定义与标注规则；文档含中期验收特征上报映射表（面部暴露面积占比→cat_face、身体面积占比→猫框等）。

#### Scenario: cat_face 类存在且有定义
- **WHEN** 查阅类目定稿文档
- **THEN** 类目清单包含 `cat_face`，且有可执行的标注边界定义（何时标、框到哪里）

#### Scenario: t13-1 任务描述与文档一致
- **WHEN** 读取 tasks.json 的 t13-1 description
- **THEN** 其类目表述引用定稿文档（含 cat_face），不再是无出处的裸清单

### Requirement: 骨架复活验证实验排期记录

tasks.json 的 t13-1 SHALL 携带排期记录：检测模型验收后第一周执行 wiki《复活条件分析》中的验证实验（门控通过率、AP-10K conf 分布、人工抽检）。

#### Scenario: 排期 note 存在
- **WHEN** 读取 t13-1 的 progress/description
- **THEN** 包含指向该实验与 wiki 文档链接的排期条目
