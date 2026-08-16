## Purpose

校方周报 Markdown 一键生成符合度小满格式要求的 docx 文档，统一模板、跨平台可用、CI 可选集成。

## ADDED Requirements

### Requirement: CLI 脚本可调用

系统 SHALL 提供 `scripts/md_to_docx.sh` 脚本，接受一个或多个 Markdown 输入（文件、目录、通配符），对每个 `.md` 调用 pandoc 生成同名同目录 `.docx`。

#### Scenario: 单文件输入
- **WHEN** 调用 `bash scripts/md_to_docx.sh management/weekly/2026/W33-郑鑫裕.md`
- **THEN** 同目录下生成 `W33-郑鑫裕.docx`

#### Scenario: 目录输入（递归）
- **WHEN** 调用 `bash scripts/md_to_docx.sh management/weekly/2026/`
- **THEN** 该目录下（含子目录）每个 `.md` 对应生成同名 `.docx`

#### Scenario: 通配符输入
- **WHEN** 调用 `bash scripts/md_to_docx.sh 'management/weekly/2026/W3*.md'`
- **THEN** 匹配到的每个 md 生成 docx

#### Scenario: 无 .md 文件
- **WHEN** 调用时未匹配到任何 `.md`
- **THEN** 脚本退出码非零并打印"未找到 .md 文件"提示

### Requirement: 使用 reference docx 模板

脚本 SHALL 使用 `templates/docx-reference.docx` 作为 pandoc 的 `--reference-doc`，保证所有生成的 docx 样式一致。

#### Scenario: 模板存在
- **WHEN** 模板文件存在
- **THEN** pandoc 调用传入 `--reference-doc=templates/docx-reference.docx`

#### Scenario: 模板缺失
- **WHEN** `templates/docx-reference.docx` 不存在
- **THEN** 脚本退出码非零并提示"模板缺失，请先准备 templates/docx-reference.docx"

### Requirement: 输出位置与覆盖

默认 SHALL 输出到同目录同名 `.docx`（不修改 Markdown 源文件）；同一 docx 已存在 SHALL 覆盖。

#### Scenario: 同目录输出
- **WHEN** 处理 `path/to/X.md`
- **THEN** 输出 `path/to/X.docx`

#### Scenario: 已存在则覆盖
- **WHEN** 目标 docx 已存在
- **THEN** 覆盖（不要求确认）

### Requirement: 模板覆盖参数

脚本 SHALL 接受 `--ref-doc PATH` 参数，指定后覆盖默认模板路径，便于临时测试不同模板。

#### Scenario: 自定义模板
- **WHEN** 调用 `bash scripts/md_to_docx.sh --ref-doc /tmp/my.docx management/weekly/2026/W33-郑鑫裕.md`
- **THEN** pandoc 使用 `/tmp/my.docx` 作为模板生成 docx

### Requirement: 安装说明

仓库 SHALL 在 `templates/README.md` 或脚本头部说明中提供 pandoc 安装指引，覆盖 macOS（brew）、Linux（apt）、conda 三条路径，命令可直接复制执行。

#### Scenario: 安装指引可读
- **WHEN** 用户查看安装指引
- **THEN** 至少包含 macOS `brew install pandoc`、Linux `apt install pandoc`、conda `conda install -c conda-forge pandoc` 中的一条具体命令

### Requirement: Starter 模板可立即使用

仓库 SHALL 在 `templates/docx-reference.docx` 提供一份 starter docx（pandoc 默认 docx + 基础中文表格/标题样式调整），无需任何额外配置即可让脚本跑通。

#### Scenario: 模板可用
- **WHEN** 首次拉取仓库运行脚本
- **THEN** 脚本能直接生成可打开、样式可读的 docx（无需用户先制作模板）