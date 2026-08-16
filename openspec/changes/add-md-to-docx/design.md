## Context

- macOS 上 `pandoc 3.8.1` 已通过 homebrew 装好；Linux（pet）`apt install pandoc` 即可
- 周报 md 在 `management/weekly/2026/`，含中文、表格、代码块、任务列表
- 度小满原表格式：事项 / 具体内容 / 计划完成时间 三列（参考 08-07 张凤老师表）
- 仓库无 `templates/` 目录、无任何 pandoc/docx 资产；scripts/ 现有 Python 脚本为主，本次新增 bash 即可

## Goals / Non-Goals

**Goals:**

- 一行命令：`bash scripts/md_to_docx.sh management/weekly/2026/` 生成所有周报 docx
- 模板即装即用：starter docx 提交即生效，无需用户先制作
- 跨平台：macOS / Linux 都能跑

**Non-Goals:**

- 不做 Web UI 触发
- 不做 GitHub Actions 自动上传
- 不做周报以外的文档（task book、phase2 计划等暂不纳入；如需后续另立变更）
- 不做实时预览 / 增量编译

## Decisions

### D1：脚本语言 Bash + 极简封装

- 理由：pandoc 单行调用即可，bash 比 Python 启动快、无依赖
- 一行核心：`pandoc --reference-doc="$ref_doc" -o "$out" "$in"`
- 备选 Python：否决（杀鸡用牛刀，且 scripts/ 里 Python 已经有更重的依赖）

### D2：默认输出与源同目录同名 `.docx`

- 理由：度小满拿 docx 时需要能直接对应到 md（文件名一致最直观）
- 备选：输出到 `dist/docx/...` 保留目录结构——否决（增加心智负担，且度小满不关心仓库目录结构）

### D3：模板路径硬编码为 `templates/docx-reference.docx`

- 仓库内置 starter 模板（pandoc 默认 docx 基础上微调）
- 用户可通过 `--ref-doc` 临时替换
- 备选：从 `~/.config/pet/docx-template.docx` 读取——否决（与 starter 模板并存会增加复杂度）

### D4：Starter 模板如何生成

- 用 pandoc 内置 reference.docx 作起点：`pandoc -o templates/docx-reference.docx --print-default-data-file reference.docx > templates/docx-reference.docx`
- 注意：pandoc 3.x 的 `--print-default-data-file reference.docx` 输出二进制到 stdout，需要重定向到文件
- 中文字体不在模板里硬编码——依赖系统字体（macOS PingFang / Linux Noto Sans CJK / Windows Microsoft YaHei）
- 备选：手工在 Word 里改样式再保存为模板——否决（不可复现、依赖图形化操作）

### D5：模板文件入 git

- 二进制 docx ~30KB，普通 git 可接受（不上 LFS）
- 若未来模板变大（如嵌入字体）再评估 LFS

### D6：递归处理目录

- `find` 遍历子目录下所有 `.md`（`find "$dir" -name '*.md' -type f`）
- 跳过 hidden（`.` 开头）的 md（避免 `.git/`、`.openspec/` 等干扰）

### D7：错误处理

- pandoc 失败：打印 stderr、退出非零（不静默）
- 单文件失败不中断整批？—— 是：脚本遇到某文件失败打印错误继续处理下一个，最终退出码 = 失败文件数（>0 表示有失败）
- 模板缺失：立即失败（这是配置问题，不应继续）

## Risks / Trade-offs

- **[R1] 中文字体跨平台差异** → 模板不嵌字体，依赖系统已有中文字体；文档里不强求特定字体；用户在度小满侧查看如有字体回退属可接受范围。
- **[R2] 度小满格式未来变更** → starter 模板是"基础可读"起点，度小满侧如有具体格式要求（如红色标题、固定行距），本地手动调整 docx-reference.docx 即可，无需改脚本。
- **[R3] docx 二进制 diff 难 review** → 模板只在变更时新提交，常规 review 看脚本与示例产物；CI 可选加 smoke test（生成 + 文件 size 检查）。
- **[R4] 大目录遍历慢** → 周报量级（< 50 份）不构成问题；脚本不递归 `.git/` 等隐藏目录避免误处理。

## Migration Plan

无存量用户（新工具）。回滚 = 删除脚本 + 模板目录，不影响现有功能。

## Open Questions

- 度小满对 docx 是否有具体样式要求（字体、行距、标题颜色等）？当前 starter 用 pandoc 默认；若后期明确需求，手动调整 `templates/docx-reference.docx` 即可（脚本不变）。