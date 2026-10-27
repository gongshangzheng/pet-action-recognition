# Sidecar JSON 指南

sidecar 与笔记同名：`management/docs/notes/<slug>.json`。正文写当前知识和解释；演进、进度、附录和关联文档写 sidecar。

```json
{
  "changelog": [{"date": "2026-09-22", "summary": "初版精读笔记"}],
  "progress": {"status": "draft", "next": "补充代码复现"},
  "appendix": [{"title": "原始图清单", "path": ".cache/article-note/<slug>/raw/figures/figures-manifest.md"}],
  "related": ["papers/<slug>", "notes/<other-slug>"]
}
```

## 四字段

- `changelog`：正文版本和重要改动，避免把历史塞回正文。
- `progress`：当前复核/复现进度和下一步。
- `appendix`：不适合正文的补充材料、原始证据路径或复现命令。
- `related`：已有 wiki 文档、论文条目或相关笔记 slug。

写入前用 JSON 解析器校验。不要把密码、API key、临时 token 或整篇 raw 文本放入 sidecar。
