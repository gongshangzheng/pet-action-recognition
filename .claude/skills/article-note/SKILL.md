---
name: article-note
description: 论文精读与 Markdown wiki 笔记流水线：先抓素材和分析，再生成 OpenSpec 结构，经用户确认后写入 management/docs/notes/；支持按需委派独立分析与图片落盘。
---

# article-note

## 适用场景

用户提供论文链接、arXiv ID、PDF、标题或代码仓库，并要求精读、解读、整理笔记、论文分析或复现要点时使用。

## 核心门禁

严格遵循：

```text
素材 → 分析 → synthesis 索引 → OpenSpec change + 详细结构 → 向用户汇报 → 明确确认 → 图片发布/正文/sidecar → 校验
```

在用户明确确认结构前，禁止创建或修改 `management/docs/notes/` 下的笔记正文和 sidecar。素材只能放在 `.cache/article-note/<slug>/`。

## 运行模式

- **direct（默认）**：主 agent 独立完成分析，适合短文或材料完整的论文。
- **assisted**：把 1–3 个相对独立、耗 token 的分析 lane 交给 subagent。
- **deep**：并行委派多个独立 lane，适合长论文、复杂实验、代码复现或配图较多的论文。

subagent 是可选分析模板，不是固定启动清单。主 agent 负责选择 lane、综合事实、处理冲突、生成 change、获取确认和撰写正文。

## Phase 总览

1. **Extraction**：初始化工作区，按 source → HTML → PDF 抓取材料、元信息和候选图片。
2. **Analysis**：主 agent 直接分析，或按需委派 background / methodology / experiment / terminology / citation / code-analysis / image-collection。
3. **Index**：生成简短的 `synthesis.md`，只做事实位置索引、交叉引用、冲突标记和写作分配。
4. **Change**：基于真实素材创建 `docs-notes-<slug>`，在 design 中写完整笔记结构。
5. **Approval**：向用户汇报结构、图表公式清单和缺料项，等待明确确认。
6. **Writing**：确认后发布选定图片、撰写 Markdown 和 sidecar，执行交付校验。

对应文件：`phases/1-extraction.md` 至 `phases/5-writing.md`；第五份文件承载 Phase 6 撰写。

## 固定脚本

在 `scripts/` 下：

- `init-workspace.py`：初始化工作区，不覆盖已有文件。
- `fetch-paper.py`：抓取 arXiv source/HTML/PDF，提取正文、元信息和原图。
- `figures.py`：检查、转换和显式发布图片到 `_assets/`。
- `validate-analysis.py`：校验分析 lane、来源指针和 synthesis。
- `validate-note.py`：校验 frontmatter、标题层级、公式、图片、链接和 sidecar。
- `check-delivery.py`：汇总 OpenSpec、工作区、笔记、资产和 Git 检查。

脚本默认不写 `management/docs/notes/`、不删除、不覆盖、不提交；提供 `--help` 和 check/dry-run 模式。

## 输出位置

```text
.cache/article-note/<slug>/              # gitignored 素材和分析
management/docs/notes/<slug>.md          # 用户确认后创建
management/docs/notes/<slug>.json        # sidecar
management/docs/_assets/<slug>/          # 用户确认后发布的图片
```

最终笔记 frontmatter 只使用 `title`、`author`、`date`、`tags`、`summary`，可选 `id`。arXiv、venue、代码仓库和原文链接放在正文“论文信息”表格。

## Subagent 边界

subagent 只读取素材、提取事实、标注来源、指出矛盾/缺口和提出结构建议。输出格式为“事实 + 来源指针 + 不确定性”，写入 `analysis/`。不得创建 OpenSpec change、写最终笔记或绕过用户确认。

## 质量底线

- 关键结论可回溯到 raw 或 analysis 文件。
- 未披露配置写“未披露”，不得猜测。
- 标题只使用 `##` 与 `###`。
- 公式直接用 LaTeX（行内 `$...$`、块级 `$$...$$`），渲染器会走 KaTeX；仍须配套符号表与中文解释。
- Mermaid 图内公式只支持 `$$...$$`（单 `$` 不渲染，是 Mermaid 自身规则）。
- 图片使用绝对 `/api/management/docs-assets/<slug>/...` URL；优先 WebP，最长边 ≤1600px、单图 ≤500KB、单篇 ≤5MB。
- 常规论文尽量保留至少 3 张能替代文字的原图，每图必须有图题和正文解读。
- `[[slug]]` 链接必须指向真实存在的文档或任务。
- Mermaid、sidecar JSON、OpenSpec change 和 Git diff 均须可验证。

## 故障处理

source、HTML、PDF 全部失败时停止，不凭标题写作；把失败原因写入 extraction-log 并报告。缺少 Pillow/PyMuPDF 时保留原图并提示。发现大纲与正文不一致时，先用 `openspec-update-change` 更新 design，不能静默偏离。

## 参考资料

- `phases/1-extraction.md`：素材抓取
- `phases/2-analysis.md`：分析委派
- `phases/3-index.md`：synthesis
- `phases/4-change.md`：OpenSpec 与审批
- `phases/5-writing.md`：Markdown 写作与交付
- `references/note-structure-template.md`：10 节笔记骨架
- `references/paper-section-guide.md`：论文分节利用方式
- `references/sidecar-guide.md`：sidecar 字段约定
