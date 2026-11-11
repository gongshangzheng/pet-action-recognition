#!/usr/bin/env bash
# 把 Mermaid 源文件渲染成 PNG（2 倍超采样）+ SVG。
#
# 用法：
#   render_mermaid.sh <input.mmd> [输出基名] [画布宽度=1900]
#
# 说明：
# - 主题由同目录 mermaid-render-config.json 经 `-c` 传入。不要改用 %%{init}%% 指令：
#   mmdc 12.0.0 + mermaid 12.1.0 下 init 里的 themeVariables 实测不生效。
# - Chrome 路径按 CHROME_BIN 或本机 puppeteer 缓存探测，只在运行时生成的临时配置里出现，不入库。
# - 输出一律覆盖同名文件；图的可编辑源是 .mmd，不要手改 PNG。
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <input.mmd> [输出基名] [画布宽度=1900]" >&2
  exit 2
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT="$1"
OUT_BASE="${2:-${INPUT%.mmd}}"
WIDTH="${3:-1900}"
CONFIG="${MERMAID_CONFIG:-$SKILL_DIR/scripts/mermaid-render-config.json}"

[ -f "$INPUT" ] || { echo "input not found: $INPUT" >&2; exit 1; }
[ -f "$CONFIG" ] || { echo "render config not found: $CONFIG" >&2; exit 1; }

CHROME="${CHROME_BIN:-}"
if [ -z "$CHROME" ]; then
  CHROME="$(find "$HOME/.cache/puppeteer/chrome-headless-shell" -type f -name 'chrome-headless-shell' 2>/dev/null | sort | tail -1)"
fi
if [ -z "$CHROME" ] || [ ! -x "$CHROME" ]; then
  echo "未找到 chrome-headless-shell，先执行： npx puppeteer browsers install chrome-headless-shell" >&2
  exit 1
fi

WORK_DIR="$(mktemp -d)"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

cat > "$WORK_DIR/puppeteer.json" <<JSON
{
  "executablePath": "$CHROME",
  "args": ["--no-sandbox", "--disable-setuid-sandbox"],
  "defaultViewport": { "width": $WIDTH, "height": 1200, "deviceScaleFactor": 1 }
}
JSON

mmdc -q -p "$WORK_DIR/puppeteer.json" -c "$CONFIG" -i "$INPUT" -o "$OUT_BASE.png" -s 2 -b '#ffffff'
mmdc -q -p "$WORK_DIR/puppeteer.json" -c "$CONFIG" -i "$INPUT" -o "$OUT_BASE.svg" -b '#ffffff'

echo "rendered: $OUT_BASE.png"
echo "rendered: $OUT_BASE.svg"
