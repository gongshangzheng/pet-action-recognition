## Why

度小满要求周报以 docx 形式提交（参考 08-07 张凤老师发来的格式：事项 / 具体内容 / 计划完成时间 三列表）。当前周报以 Markdown 写在 `management/weekly/2026/` 下，校方手动转 docx 效率低、易出错。增加一个本地 CLI 流程，把 `management/weekly/**/*.md` 一键生成同目录 `.docx`，用统一 reference docx 模板保证度小满侧的样式一致性。

## What Changes

- **新增 CLI 脚本** `scripts/md_to_docx.sh`：接受单文件/目录/通配符，调用 pandoc 生成 docx，输出到同目录
- **新增 starter 模板** `templates/docx-reference.docx`：仓库内置一份可立即使用的样式起点（pandoc 默认 + 中文表格/标题调整），后续可替换
- **新增 macOS / Linux 安装说明**：brew / apt / conda 三条路径，README 顶部一句指向
- **不改动**：周报模板本身、Web UI、其他模块

## Capabilities

### New Capabilities

- `tools/md-to-docx`：周报 Markdown → docx 转换流程——CLI 脚本、reference 模板、跨平台安装说明

### Modified Capabilities

无

## Impact

- 新增脚本：`scripts/md_to_docx.sh`（bash，单文件）
- 新增模板：`templates/docx-reference.docx`（二进制 docx，git LFS？先试普通 git，docx ~30KB 可接受）
- 新增外部依赖：`pandoc` 3.x（本地安装，CI 可选）
- 用户：执行 `bash scripts/md_to_docx.sh management/weekly/2026/` 即可一键生成所有周报 docx
- 不影响：训练 / 评测 / live / papers / speedrun 各模块