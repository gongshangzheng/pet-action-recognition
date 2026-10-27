# Phase 5/6：Writing 与交付

仅在用户确认结构后执行。

## 顺序

1. 运行 `figures.py inspect/convert`，只发布已选图片：`figures.py publish`。
2. 创建 `management/docs/notes/<slug>.md` 与同名 `.json` sidecar。
3. 按 change design 逐节写作；偏离时先更新 change。
4. 运行 `validate-note.py` 和 `check-delivery.py`。

## Markdown 适配

- frontmatter 只含 `title/author/date/tags/summary`，可选 `id`。
- 顶层用 `##`，次级用 `###`，不使用 `####`。
- 公式用 LaTeX：行内 `$...$`、块级 `$$...$$`（渲染为 KaTeX）；随后给符号表和中文解释。
- 源论文记号需要保真时，可额外附 fenced code block 保留原式（可选）。
- 图片用 `![图 N · 说明](/api/management/docs-assets/<slug>/<file>)`；图号连续，每图在正文有解读。
- 流程和模块关系用 Mermaid；表格过宽时拆表或转纵向表。
- 内部文档使用 `[[slug]]` 或 `[[slug|label]]`。

## 交付自检

核对来源可追溯、未披露项、图片 URL/体积、sidecar JSON、内部链接、Mermaid、TOC 层级、OpenSpec 状态和 Git diff。脚本只报告问题，不代替主 agent 判断。