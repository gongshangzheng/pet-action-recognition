# Templates

本目录存放项目文档模板，目前含 docx 引用模板供 `scripts/md_to_docx.sh` 使用。

## `docx-reference.docx`

周报 Markdown → docx 转换的 pandoc 引用模板（reference-doc），保证所有生成的 docx 样式一致。

### 重新生成 starter 模板

当前模板来自 pandoc 内置 reference（11KB，零样式定制）。如需重新生成：

```bash
pandoc --print-default-data-file reference.docx > templates/docx-reference.docx
```

### 自定义样式

如需调整标题/表格/字体等样式：

1. 在 Word / Pages / LibreOffice 打开 `templates/docx-reference.docx`，修改样式并另存覆盖
2. 或：基于现有模板跑一次示例转换得到 docx，修改后再保存为 `docx-reference.docx`（此为 pandoc 官方推荐流程）

注意：模板里**不要硬编码特定字体**，依赖系统已有中文字体（macOS PingFang / Linux Noto Sans CJK / Windows Microsoft YaHei）。

### 在脚本中临时使用其他模板

```bash
bash scripts/md_to_docx.sh --ref-doc /path/to/other.docx input.md
```

## pandoc 安装

`md_to_docx.sh` 依赖外部 `pandoc`（≥ 3.x）。安装命令：

| 系统 | 命令 |
|---|---|
| macOS | `brew install pandoc` |
| Linux (apt) | `sudo apt install pandoc` |
| conda | `conda install -c conda-forge pandoc` |

安装后验证：`pandoc --version` 应输出 3.x 版本号。