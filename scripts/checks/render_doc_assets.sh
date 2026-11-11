#!/usr/bin/env bash
# 兼容入口：渲染管理文档里的 Mermaid 图为 PNG/SVG。
#
# 真正的实现在 report-figures skill 里（主题配置、Chrome 探测、2 倍超采样都在那边），
# 这里只做转发，不重复维护同一套逻辑。
#
# 用法：
#   scripts/checks/render_doc_assets.sh <input.mmd> [output_basename] [画布宽度]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RENDERER="$REPO_ROOT/.claude/skills/report-figures/scripts/render_mermaid.sh"

if [ ! -x "$RENDERER" ]; then
  echo "找不到 report-figures skill 的渲染脚本：$RENDERER" >&2
  exit 1
fi

exec "$RENDERER" "$@"
