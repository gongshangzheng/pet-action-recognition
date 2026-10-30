## ADDED Requirements

### Requirement: 文字对比度达 WCAG AA

全站正文、次要文字、占位符与空态描述 SHALL 在其实际底色上达到 4.5:1（大字号 3:1）；明暗两种模式 SHALL 各自使用满足该阈值的色值。

#### Scenario: 浅色模式次要文字
- **WHEN** 浅色模式下渲染 `--color-text-dim` 承载的日期、负责人、说明等文字
- **THEN** 在卡片白底与 elevated 底色上对比度均 ≥4.5:1

#### Scenario: 深色模式次要文字
- **WHEN** 深色模式下渲染同一批文字
- **THEN** 在深色卡片与 elevated 底色上对比度均 ≥4.5:1，MUST NOT 沿用浅色模式色值

#### Scenario: 占位符与空态描述
- **WHEN** 输入框/选择器为空或页面无数据
- **THEN** 占位符与空态描述文字对比度 ≥4.5:1，MUST NOT 使用 Naive UI 默认的 #c2c2c2 / 38% 白

### Requirement: 可点击卡片键盘可达

以卡片/列表项形式承载点击跳转的元素 SHALL 可被键盘聚焦并激活，且 SHALL 暴露按钮或链接语义。

#### Scenario: 键盘聚焦可点卡片
- **WHEN** 用户用 Tab 遍历论文列表、数据集、Speed Run 结果或文档侧栏
- **THEN** 每个可点项都进入焦点序列，并显示可见焦点指示

#### Scenario: 键盘激活
- **WHEN** 焦点落在可点卡片上并按 Enter 或 Space
- **THEN** 触发与鼠标点击相同的动作

### Requirement: 每页有唯一一级标题

除正文自带可见 `h1` 的页面外，每个路由 SHALL 提供且仅提供一个 `h1`，页内后续标题 SHALL 从 `h2` 开始，不跳级。

#### Scenario: 无可见标题的页面
- **WHEN** 打开任务看板、数据集、训练结果等以卡片承载内容的页面
- **THEN** 文档中恰有一个 `h1`（可视觉隐藏），其文本为该页标题

#### Scenario: 已有可见标题的页面
- **WHEN** 打开文档、报告或会议纪要页
- **THEN** 只有正文那个可见 `h1`，不额外注入隐藏 `h1`

### Requirement: 内容区为主地标且可跳过导航

内容区 SHALL 是 `<main>` 地标，并提供键盘可用的「跳到主内容」入口。

#### Scenario: 跳到主内容
- **WHEN** 键盘用户在页面首次按 Tab
- **THEN** 出现可聚焦的跳转链接，激活后焦点进入主内容区

### Requirement: 窄屏下无控件被裁切

在 320px 至 768px 宽度下，多列网格 SHALL 按断点降列，顶栏交互元素 SHALL 完整可见且可点击，页面 MUST NOT 出现横向溢出。

#### Scenario: 手机宽度下的卡片网格
- **WHEN** 在 390px 宽度打开首页、任务看板、团队成员、模型管理或 Speed Run
- **THEN** 网格列宽不小于 140px，或降为单列

#### Scenario: 顶栏交互元素
- **WHEN** 在 320px 宽度查看顶栏
- **THEN** 主题、调色盘按钮完整位于视口内，可点击
