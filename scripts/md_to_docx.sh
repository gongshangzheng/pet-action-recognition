#!/usr/bin/env bash
# md_to_docx.sh — 周报 Markdown → docx 转换（pandoc + reference 模板）
#
# 用法:
#   bash scripts/md_to_docx.sh management/weekly/2026/W33-郑鑫裕.md
#   bash scripts/md_to_docx.sh management/weekly/2026/             # 整个目录递归
#   bash scripts/md_to_docx.sh 'management/weekly/2026/W3*.md'    # 通配符
#   bash scripts/md_to_docx.sh --ref-doc /tmp/other.docx file.md  # 自定义模板
#
# 输出：每个 <input>.md 在同目录生成同名 .docx（已存在则覆盖）
# 退出码：0=全部成功，>0=失败文件数（单文件失败不中断整批）
#
# 依赖：pandoc ≥ 3.x；模板 templates/docx-reference.docx

set -u

# --- 默认模板路径（相对仓库根） ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEFAULT_REF_DOC="$REPO_ROOT/templates/docx-reference.docx"

# --- 参数解析 ---
REF_DOC="$DEFAULT_REF_DOC"
INPUTS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ref-doc)
            REF_DOC="$2"; shift 2 ;;
        --help|-h)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        --*)
            echo "未知参数: $1" >&2; exit 2 ;;
        *)
            INPUTS+=("$1"); shift ;;
    esac
done

# --- 模板缺失检测 ---
if [[ ! -f "$REF_DOC" ]]; then
    echo "错误：模板不存在: $REF_DOC" >&2
    echo "请先准备该文件，或用 --ref-doc 指定其他模板" >&2
    exit 1
fi

# --- pandoc 可用性 ---
if ! command -v pandoc >/dev/null 2>&1; then
    echo "错误：pandoc 未安装；见 templates/README.md" >&2
    exit 1
fi

# --- 展开输入为文件列表 ---
files=()
for input in "${INPUTS[@]}"; do
    if [[ -f "$input" ]]; then
        files+=("$input")
    elif [[ -d "$input" ]]; then
        # 递归找 .md，跳过 hidden（避免 .git/、.openspec/）
        while IFS= read -r f; do
            files+=("$f")
        done < <(find "$input" -type f -name '*.md' -not -path '*/\.*')
    elif [[ "$input" == *"*"* ]] || [[ "$input" == *"?"* ]]; then
        # 通配符展开（shopt 兼容）
        shopt -s nullglob
        for f in $input; do
            [[ -f "$f" ]] && files+=("$f")
        done
        shopt -u nullglob
    else
        echo "警告：跳过不存在的输入: $input" >&2
    fi
done

if [[ ${#files[@]} -eq 0 ]]; then
    echo "错误：未找到 .md 文件（输入: ${INPUTS[*]:-无}）" >&2
    exit 1
fi

# --- 逐文件转换 ---
fail_count=0
for md in "${files[@]}"; do
    out="${md%.md}.docx"
    if pandoc --reference-doc="$REF_DOC" -o "$out" "$md"; then
        echo "✓ $md → $out"
    else
        echo "✗ $md（pandoc 失败）" >&2
        fail_count=$((fail_count + 1))
    fi
done

if [[ $fail_count -gt 0 ]]; then
    echo "完成，$fail_count 个文件失败" >&2
    exit $fail_count
fi
echo "完成，全部 ${#files[@]} 个文件成功"