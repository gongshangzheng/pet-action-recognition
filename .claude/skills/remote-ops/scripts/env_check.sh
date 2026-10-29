#!/bin/bash
# 环境核验：确认「远端跑的确实是评审过的那份代码 + 那个环境」，并把结果落盘成 env.json。
#
# 用法：
#   bash env_check.sh                                  # 只打印
#   bash env_check.sh --expect-commit <sha>            # 远端 HEAD 必须等于该 commit（不等则退出码 3）
#   bash env_check.sh --env plf                        # 期望的 conda 环境名
#   bash env_check.sh --checkpoint ~/xxx/weights.pth   # 检查权重存在与大小
#   bash env_check.sh --json results/<topic>/<run-id>/env.json
#
# 退出码：0 通过 / 1 连不上 / 3 代码或环境不符合预期
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_remote_common.sh"

EXPECT_COMMIT=""
EXPECT_ENV=""
CHECKPOINT=""
JSON_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --expect-commit) EXPECT_COMMIT="$2"; shift 2 ;;
    --env) EXPECT_ENV="$2"; shift 2 ;;
    --checkpoint) CHECKPOINT="$2"; shift 2 ;;
    --json) JSON_PATH="$2"; shift 2 ;;
    --help|-h) sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
done

REMOTE_SCRIPT=$(cat <<'EOS'
set -u
root="$1"; expect_commit="$2"; expect_env="$3"; checkpoint="$4"
cd "$root" 2>/dev/null || { echo "__FAIL__ 远端目录不存在: $root"; exit 3; }
commit=$(git rev-parse HEAD 2>/dev/null || echo unknown)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "code_commit=$commit"
echo "code_branch=$branch"
echo "code_dirty_files=$dirty"
# 非交互 ssh 不会 activate conda：按环境名直接定位解释器，避免"报的是系统 python"
if [[ -n "$expect_env" ]]; then
  PY="$HOME/miniconda3/envs/$expect_env/bin/python"
  [[ -x "$PY" ]] || { echo "__FAIL__ conda 环境不存在: $expect_env ($PY)"; exit 3; }
  echo "conda_env=$expect_env"
else
  PY=$(command -v python3)
fi
echo "interpreter=$PY"
"$PY" - <<'PY' 2>/dev/null || true
import json
mods = {}
for name in ("torch", "torchvision", "numpy", "cv2", "transformers", "decord"):
    try:
        module = __import__(name)
        mods[name] = getattr(module, "__version__", "unknown")
    except Exception:
        mods[name] = None
try:
    import torch
    mods["cuda"] = torch.version.cuda
    mods["cuda_available"] = bool(torch.cuda.is_available())
except Exception:
    pass
print("libs=" + json.dumps(mods, ensure_ascii=False))
PY
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,name,driver_version,clocks.sm,power.draw,power.limit,memory.total \
    --format=csv,noheader 2>/dev/null | sed 's/^/gpu_row=/'
fi
if [[ -n "$checkpoint" ]]; then
  if [[ -e "$checkpoint" ]]; then
    size=$(du -sh "$checkpoint" 2>/dev/null | awk '{print $1}')
    echo "checkpoint=$checkpoint size=$size"
  else
    echo "__FAIL__ 权重不存在: $checkpoint"; exit 3
  fi
fi
if [[ -n "$expect_commit" ]]; then
  case "$commit" in
    "$expect_commit"*) echo "commit_match=yes" ;;
    *) echo "__FAIL__ 远端 commit=$commit 与期望 $expect_commit 不一致"; exit 3 ;;
  esac
fi
[[ -n "$expect_env" ]] && echo "env_match=yes"
if [[ "$dirty" != "0" ]]; then echo "note=远端有 $dirty 个未提交文件（可能是 tmp/，请人工确认）"; fi
exit 0
EOS
)

OUTPUT=$(ssh "${SSH_OPTS[@]}" "$REMOTE" "bash -s -- '$REMOTE_ROOT' '$EXPECT_COMMIT' '$EXPECT_ENV' '$CHECKPOINT'" <<< "$REMOTE_SCRIPT" 2>/dev/null)
RC=$?

echo "### 环境核验（${REMOTE}:${REMOTE_ROOT}）"
if (( RC == 255 )); then
  echo "无法连接 $REMOTE" >&2
  exit 1
fi
echo "$OUTPUT"

if grep -q '__FAIL__' <<< "$OUTPUT"; then
  echo "### 环境不符合预期（退出码 3）" >&2
  [[ -n "$JSON_PATH" ]] && { mkdir -p "$(dirname "$JSON_PATH")"; printf '{"time":"%s","exit_code":3,"raw":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(printf '%s' "$OUTPUT" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" > "$JSON_PATH"; }
  exit 3
fi

if [[ -n "$JSON_PATH" ]]; then
  mkdir -p "$(dirname "$JSON_PATH")"
  printf '%s' "$OUTPUT" | python3 -c '
import json, sys, datetime
fields = {}
raw = sys.stdin.read()
for line in raw.splitlines():
    if "=" in line:
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip()
print(json.dumps({"time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "exit_code": 0, "fields": fields, "raw": raw.strip().splitlines()},
                 ensure_ascii=False, indent=2))
' > "$JSON_PATH"
  echo "  env.json → $JSON_PATH"
fi
echo "### ENV OK"
exit 0
