---
name: article-note-image-collection
description: 筛选支撑结论的论文原图，记录来源、文件和笔记章节映射。
---

# Image collection lane

## 输入与优先级

检查 `raw/figures/`、source tarball、HTML figure URL、PDF 页面和用户提供截图。优先 source 内嵌图，其次 HTML，再次用户截图。

## 输出

写入 `analysis/image-collection.md`，必须包含候选表：

| 编号 | 原图图题 | 来源位置/锚点 | 候选文件 | 支撑的结论 | 建议笔记节 | 是否采用 |
|---|---|---|---|---|---|---|

随后写：

- `## 价值判断`：这张图能替代哪段文字、关键读数是什么。
- `## 缺口与替代`：取不到时使用表格重排或文字+原文锚点。
- `## 处理建议`：裁剪、命名、WebP 约束。

## 硬规则

不改画数据、不自动选择全部图片、不把装饰图列为必选图。候选文件必须真实存在或明确标记为远程来源。
