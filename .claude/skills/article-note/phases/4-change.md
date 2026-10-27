# Phase 4：OpenSpec change 与结构审批

## 创建 change

素材、分析和 synthesis 就绪后再创建：

```bash
openspec new change docs-notes-<slug>
```

不要在此之前创建 `management/docs/notes/` 正文。

## design.md 必须包含 7 个字段

1. 论文速览：标题、作者/单位、venue/年份、arXiv ID、代码仓库、原文链接。
2. 一句话价值主张（≤100 字）。
3. 笔记结构大纲：每节要点、素材来源、必备表/公式/图/代码/Mermaid、字数、缺料替代。
4. 口径与取舍：省略章节和理由。
5. 图表公式清单：表格列、公式与符号表、Mermaid、拟使用图片。
6. 引用关系：已有 wiki 的 `[[...]]` 链接与 sidecar related 计划。
7. 风险与待确认项：缺料、存疑结论和需用户裁决的问题。

结构大纲必须依据实际素材，不可写空泛承诺。

## 汇报与门禁

向用户展示完整大纲表格、图表公式清单、缺料和待确认项，并明确询问：

> 结构是否确认？确认后我按此写正文。

在得到“确认”“按此写”“直接写”等明确授权前，不得创建或修改 `management/docs/notes/` 下任何文件。用户要求修改结构时，先更新 change design 再继续。
