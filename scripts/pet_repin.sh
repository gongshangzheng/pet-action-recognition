#!/usr/bin/env bash
# pet_repin.sh — pet 的 frp IP 变了导致 ssh 不通时，重新解析活节点 IP 并更新 ~/.ssh/config。
#
# 背景：pet 走 remote.mghus.top frp（动态电信宽带，重拨换 IP）；~/.ssh/config 把 pet 的
# HostName pin 到具体 IP。pin 的 IP 失效 → ssh 超时。本脚本 dig 出所有 frp 节点 →
# 逐个 nc 探活 → 把 HostName 改成活 IP + 清旧 known_hosts 条目。
#
# 用法：bash scripts/pet_repin.sh
# 依赖：dig (bind)、nc (netcat)、python3（改 config 用）
set -euo pipefail

HOST_ALIAS="${PET_ALIAS:-pet}"
PORT="${PET_PORT:-22108}"
DOMAIN="${PET_DOMAIN:-remote.mghus.top}"

CONFIG="${HOME}/.ssh/config"

echo "=== 当前 $HOST_ALIAS HostName ==="
CURRENT_IP=$(awk -v h="$HOST_ALIAS" '
  $1=="Host" && $2==h {f=1; next}
  f && $1=="HostName" {print $2; exit}
' "$CONFIG" 2>/dev/null || true)
echo "  pinned: ${CURRENT_IP:-(none)}"

echo "=== resolve $DOMAIN ==="
IPS=$(dig +short "$DOMAIN" A 2>/dev/null | grep -E '^[0-9.]+$')
if [ -z "$IPS" ]; then
  echo "[error] DNS 解析为空：$DOMAIN 不通或 DNS 挂了" >&2
  exit 1
fi
echo "  candidates: $(echo "$IPS" | tr '\n' ' ')"

echo "=== probe alive (port $PORT, 6s each) ==="
ALIVE=""
for ip in $IPS; do
  if nc -z -w 6 -G 6 "$ip" "$PORT" 2>/dev/null; then
    echo "  $ip:$PORT ALIVE ✓"
    ALIVE="$ip"
    break
  else
    echo "  $ip:$PORT dead"
  fi
done

if [ -z "$ALIVE" ]; then
  echo "[error] 所有节点 $PORT 都不通；frp 可能整体挂了，找 wyy 修 frps/路由器。" >&2
  exit 1
fi

if [ "$ALIVE" = "$CURRENT_IP" ]; then
  echo "[ok] 当前 pin 的 IP $CURRENT_IP 仍活，无需重 pin。"
  echo "      （ssh 还是不通的话，可能是 host-key 变了：ssh-keygen -R \"[$CURRENT_IP]:$PORT\" 再连）"
  exit 0
fi

echo "=== repin $HOST_ALIAS HostName: ${CURRENT_IP:-(none)} → $ALIVE ==="
python3 - "$CONFIG" "$HOST_ALIAS" "$ALIVE" <<'PY'
import sys, re
path, alias, new_ip = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
out, in_block = [], False
changed = False
for ln in lines:
    stripped = ln.strip()
    if stripped.startswith("Host ") and stripped.split() == ["Host", alias]:
        in_block = True
    if in_block and re.match(r"^\s*HostName\s+", ln):
        ln = re.sub(r"(\bHostName\s+).*", r"\g<1>" + new_ip, ln)
        changed = True
    out.append(ln)
    # 离开 block：遇到下一个 Host 头
    if in_block and stripped.startswith("Host ") and stripped.split() != ["Host", alias]:
        in_block = False
if not changed:
    print(f"[warn] 没找到 Host {alias} 的 HostName 行；未改动。", file=sys.stderr)
    sys.exit(1)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.writelines(out)
import os; os.replace(tmp, path)
print(f"[ok] {alias} HostName -> {new_ip}")
PY

echo "=== clear stale known_hosts (${CURRENT_IP}) ==="
if [ -n "$CURRENT_IP" ]; then
  ssh-keygen -R "$CURRENT_IP" 2>/dev/null || true
  ssh-keygen -R "[${CURRENT_IP}]:${PORT}" 2>/dev/null || true
fi

echo "[done] pet HostName=$ALIVE。再 ssh pet 试。"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$HOST_ALIAS" 'echo verified: $(hostname)' || \
  echo "[warn] 重 pin 后仍连不上；可能 frp 节点抖动，稍等再试。"
