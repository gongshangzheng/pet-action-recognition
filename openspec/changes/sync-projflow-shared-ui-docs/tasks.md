## 1. 文档 API 语义

- [x] 1.1 支持 Unicode slug，拒绝空值、绝对路径和路径遍历。
- [x] 1.2 返回 folder/order 元数据，并按 folder → order → id → date(desc) → slug 稳定排序。
- [x] 1.3 扫描时跳过下划线目录，并只读挂载文档 `_assets` 静态资源。

## 2. 静态文档构建

- [x] 2.1 让构建生成器复刻 API 的元数据、目录过滤和稳定排序。
- [x] 2.2 将 `_assets` 复制到 Pages 的 `docs-assets` 发布路径。

## 3. 文档阅读体验

- [x] 3.1 增加路由级滚动位置记忆、hash 锚点优先恢复和组件清理。
- [x] 3.2 支持 Unicode 内部链接、图片资产 URL、图片图题和安全 Markdown 渲染。
- [x] 3.3 添加图片、图题和标题锚点的文档样式。

## 4. 验证与交付

- [x] 4.1 运行 Python 路由检查、静态/API 数据一致性检查、`git diff --check` 和前端生产构建。
- [x] 4.2 检查产物中的 `docs-data.json`、文档资产及与 `index.html` 一致的 `404.html`。
- [ ] 4.3 提交同步变更（注明 ProjFlow 来源），推送 `origin/main` 并确认 GitHub Pages 部署。
