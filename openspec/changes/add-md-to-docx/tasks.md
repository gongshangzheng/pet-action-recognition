## 1. 准备 starter 模板

- [x] 1.1 生成 `templates/docx-reference.docx`（`pandoc -o templates/docx-reference.docx --print-default-data-file reference.docx > templates/docx-reference.docx`），确认文件可正常打开
- [x] 1.2 写 `templates/README.md`：说明 pandoc 安装命令（brew / apt / conda 三条）+ 模板替换方法

## 2. CLI 脚本

- [x] 2.1 实现 `scripts/md_to_docx.sh`：参数解析（`--ref-doc PATH`、输入文件/目录/通配符）、递归 `find`、逐文件调用 pandoc、错误隔离
- [x] 2.2 模板缺失检测：脚本开头检查 `templates/docx-reference.docx`，缺失则退出非零并提示
- [x] 2.3 加执行权限：`chmod +x scripts/md_to_docx.sh`，确保能直接 `bash scripts/md_to_docx.sh ...` 调用

## 3. 验证

- [x] 3.1 在 `management/weekly/2026/` 上跑通：`bash scripts/md_to_docx.sh management/weekly/2026/W33-郑鑫裕.md`，确认 docx 生成且文件 size 合理（>10KB）
- [x] 3.2 目录批量：`bash scripts/md_to_docx.sh management/weekly/2026/`，确认所有 md 都生成 docx
- [x] 3.3 模板缺失路径：临时 `mv templates/docx-reference.docx /tmp/` 后运行，确认脚本报错且退出非零
- [x] 3.4 用 macOS Pages 或 `textutil` 验证生成的 docx 内容完整（标题/表格/中文渲染正常）

## 4. 提交

- [ ] 4.1 git commit（`feat: 周报 md → docx 转换流程（pandoc + reference 模板）`），包含脚本 + 模板 + README